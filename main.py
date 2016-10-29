from db import insert_new_question, insert_new_user, insert_answer, \
    get_user_cursor, get_untouched_question_cursor, FLAG
from db import db_client, change_user_status, change_question_status
from constants import Magic, BS_PARSER
from logger import log
from session import get_or_create_session
from settings import EXPLORE_USER_COUNT, EXPLORE_QUESTION_COUNT, CONCURRENCY

import asyncio
import re

from bs4 import BeautifulSoup


loop = asyncio.get_event_loop()
session = loop.run_until_complete(get_or_create_session())
sem = asyncio.Semaphore(CONCURRENCY)


async def get_page_body(url: str) -> str:
    await sem.acquire()
    rsp = await session.get(url)
    data = await rsp.read()
    content = data.decode('utf-8')
    rsp.close()
    sem.release()
    return content


class Crawler:

    def __init__(self):
        self.db = db_client
        self.loop = asyncio.get_event_loop()

        # Seed user and necessary index
        insert_new_user(self.db, user_id=Magic.seed_user)

        self.db.answers.ensure_index("answer_id")
        self.db.answers.ensure_index("author")
        self.db.answers.ensure_index("relate_question")
        self.db.questions.ensure_index("question_id")
        self.db.questions.ensure_index("touched")
        self.db.users.ensure_index("touched")
        self.db.users.ensure_index("user_id")

    # Start from User Profile page:
    # - all answers, page by page
    # - question id, if they are new

    async def first_answer_page(self, user_id: str) -> (int, str, BeautifulSoup):
        max_page_link = "http://www.zhihu.com/people/" + user_id + "/answers"
        content = await get_page_body(max_page_link)
        soup = BeautifulSoup(content, BS_PARSER)
        try:
            k = soup.find("div",
                          class_=Magic.UserProfile.answer_paginator).get_text()
            max_page = [int(j) for j in re.findall('\d+', k)][-1]
        except:
            max_page = 1

        return max_page, max_page_link, soup

    def parse_and_insert_single_answer(self, user_id, answer_item):
        question_title_element = answer_item.find(Magic.hyperlink, class_=Magic.UserProfile.question)
        answer_id = int(Magic.answer_id_in_answer.findall(str(question_title_element))[0])
        if self.db.answers.find({'answer_id': answer_id}).count() == 0:
            question_id = int(Magic.UserProfile.profile_qid.findall(str(question_title_element))[0])
            insert_new_question(self.db, question_id)
            try:
                answer_content_str = answer_item.find(class_=Magic.UserProfile.content_class)
                answer_content_str = answer_content_str.get_text()
            except AttributeError:
                answer_content_str = Magic.harmony_answer

            try:
                comments_html = answer_item.find(Magic.hyperlink, class_=Magic.UserProfile.comments_count)
                comments_count = int(Magic.number.findall(str(comments_html))[0])
            except IndexError:
                comments_count = 0
            insert_answer(self.db, answer_id, user_id, question_id, comments_count, answer_content_str)

    def insert_answer_list_page(self, soup, answer_author) -> bool:
        # get all answer of that page
        all_answers = soup.find_all("div", class_=Magic.UserProfile.answer)

        # Extract answer item, and add questions if they aren't in db
        for answer_item in all_answers:
            self.parse_and_insert_single_answer(user_id=answer_author, answer_item=answer_item)

        return len(all_answers)

    async def insert_user_all_answers(self, user_id: str):
        change_user_status(db=self.db, user_id=user_id, status=FLAG.IN_USE)

        # answer page count,
        # base url of this user's answer
        # first page's soup
        page_count, base_url, soup = await self.first_answer_page(user_id=user_id)
        self.insert_answer_list_page(soup, user_id)

        # insert all others, if any
        answers = 0
        if page_count > 1:
            answers += 20
            page_range = range(2, page_count + 1)
            for page_num in page_range:
                current_page_link = base_url + "?page=" + str(page_num)
                content = await get_page_body(current_page_link)
                soup = BeautifulSoup(content, BS_PARSER)
                answers += self.insert_answer_list_page(soup, user_id)

        change_user_status(db=self.db, user_id=user_id, status=FLAG.FINISHED)

        if answers != 0:
            log.debug("Inserted {} answers for user {}.".format(answers, user_id))
        return True

    # Start from single Question page
    # - all answers
    # - new users

    def update_question_detail(self, soup_content, question_id):
        title = soup_content.find(Magic.Question.title)
        if title:
            title = title.get_text().strip()
        else:
            log.debug("Question %s didn't have title." % question_id)
            title = ""

        detail = soup_content.find('div', class_=Magic.Question.question_detail)
        if detail:
            detail = detail.get_text().strip()
        else:
            log.debug("Question %s didn't have details." % question_id)
            detail = ""

        follower = soup_content.find('div', class_=Magic.Question.follower)
        try:
            follower = Magic.number.findall(follower.get_text())[0]
        except (IndexError, AttributeError):
            # either None object have no get_text
            # or no result found..
            log.debug("Question %s didn't have follower." % question_id)
            follower = 0
        self.db.questions.update_one({'question_id': int(question_id)},
                                     {'$set': {'title': title, 'detail': detail, 'follower': follower}})

    @staticmethod
    def process_answer(bs_answer: BeautifulSoup) -> (str, int, str):
        try:
            content = str(bs_answer.find('div', class_=Magic.Question.answer_content_div).get_text())
        except AttributeError:
            # content = bs_answer.find('div', class_ = 'answer-status').get_text()
            content = Magic.harmony_answer

        try:
            author_temp = str(bs_answer.find('a',
                                             class_=Magic.Question.author_div))
            author = Magic.Question.author_name.findall(author_temp)[0]
        except IndexError:
            author = 'Anonymous'

        try:
            comment_div = str(bs_answer.find('a',
                                             class_=Magic.Question.comment_div))
            comments_count = int(Magic.number.findall(comment_div)[0])
        except IndexError:
            # no comments yet
            comments_count = 0

        return author, comments_count, content

    async def update_question_insert_answer(self, question_id: int):
        change_question_status(db=self.db,
                               question_id=question_id, status=FLAG.IN_USE)

        # Update question detail
        question_url = 'http://www.zhihu.com/question/' + str(question_id)
        question_content = await get_page_body(question_url)

        q_soup = BeautifulSoup(question_content, BS_PARSER)
        if type(q_soup.find(Magic.Question.title)) is not None:
            self.update_question_detail(q_soup, question_id)
        else:
            return True  # 404

        # First 50 answers
        answers = q_soup.findAll('div', class_=Magic.Question.answer_div)
        if len(answers) > 0:
            for answer in answers:
                answer_id = int(Magic.answer_id_in_answer.findall(str(answer))[0])

                # TODO: save different version?
                # if self.db.answers.find({'answer_id': answer_id}).count() == 1:
                #     continue  # jump by this answer

                author, comments_count, content = self.process_answer(answer)
                insert_answer(self.db, answer_id, author, question_id, comments_count, content)

        # Users
        users = set(Magic.Question.mentioned_userid.findall(str(question_content)))
        for user in users:
            insert_new_user(self.db, user)

        change_question_status(db=self.db,
                               question_id=question_id,
                               status=FLAG.FINISHED)
        return True

    def fetch_users(self):
        untouched_user_list = get_user_cursor(self.db, EXPLORE_USER_COUNT)
        user_id_list = [user["user_id"] for user in untouched_user_list]

        tasks = asyncio.wait([self.insert_user_all_answers(user_id)
                              for user_id in user_id_list])
        self.loop.run_until_complete(tasks)

        log.info("Finished crawling {} users.".format(EXPLORE_USER_COUNT))

    def fetch_questions(self):
        questions_list_cursor = get_untouched_question_cursor(self.db, EXPLORE_QUESTION_COUNT)
        question_list = [question_item["question_id"] for question_item in questions_list_cursor]
        tasks = asyncio.wait([self.update_question_insert_answer(question_id)
                              for question_id in question_list])
        self.loop.run_until_complete(tasks)

        log.info("Finished crawling {} questions.".format(EXPLORE_QUESTION_COUNT))

    def run(self):

        # reset all unfinished user/questions
        self.db.users.update_many({'touched': FLAG.IN_USE}, {'$set': {'touched': FLAG.UNTOUCHED}})
        self.db.questions.update_many({'touched': FLAG.IN_USE}, {'$set': {'touched': FLAG.UNTOUCHED}})

        # show status
        answer_count = self.db.answers.count()
        log.info("Existing answers: %s" % answer_count)

        question_count = self.db.questions.count()
        question_to_explore = self.db.questions.find({'touched': FLAG.UNTOUCHED}).count()
        explored_question = question_count - question_to_explore
        log.info("%s questions: %s new, %s crawled." %
                 (question_count, question_to_explore, explored_question))

        user_count = self.db.users.count()
        user_to_explore = self.db.users.find({'touched': FLAG.UNTOUCHED}).count()
        explored_user = user_count - user_to_explore
        log.info("%s users: %s new, %s crawled." % (user_count, user_to_explore, explored_user))

        while True:
            try:
                self.fetch_users()
                self.fetch_questions()
            except KeyboardInterrupt:
                break

if __name__ == "__main__":
    crawler = Crawler()
    crawler.run()
    session.close()
