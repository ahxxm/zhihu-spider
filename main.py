from db import insert_new_question, insert_new_user, insert_answer, get_user_cursor, get_untouched_question_cursor, FLAG
from db import db_client, change_user_status, change_question_status
from constants import Magic, BS_PARSER
from logger import log
from session import get_or_create_session
from settings import EXPLORE_USER_COUNT, EXPLORE_QUESTION_COUNT, CONCURRENCY

import re

from bs4 import BeautifulSoup
from multiprocessing.dummy import Pool as ThreadPool


class Crawler:

    def __init__(self):
        self.db = db_client
        self.session = get_or_create_session()

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

    def first_answer_page(self, user_id: str) -> (int, str, BeautifulSoup):
        max_page_link = "http://www.zhihu.com/people/" + user_id + "/answers"
        soup = BeautifulSoup(self.session.get(max_page_link).content, BS_PARSER)
        try:
            k = soup.find("div", class_=Magic.UserProfile.answer_paginator).get_text()
            max_page = [int(j) for j in re.findall('\d+', k)][-1]
        except:
            max_page = 1

        return max_page, max_page_link, soup

    def parse_and_insert_single_answer(self, user_id, answer_item):
        question_title_element = answer_item.find(Magic.hyperlink, class_=Magic.UserProfile.question)
        answer_id = int(Magic.answer_id_in_answer.findall(str(question_title_element))[0])
        if self.db.answers.find({'answer_id': answer_id}).count() == 0:
            question_id = int(Magic.UserProfile.question_id_in_user_profile.findall(str(question_title_element))[0])
            insert_new_question(self.db, question_id)
            try:
                answer_content_str = answer_item.find(class_=Magic.UserProfile.answer_content_class_in_user_profile)
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

        # No no answer found, mark as complete
        if len(all_answers) < 1:
            log.info("User %s does not have answers yet." % answer_author)

        # Extract answer item, and add questions if they aren't in db
        for answer_item in all_answers:
            self.parse_and_insert_single_answer(user_id=answer_author, answer_item=answer_item)

        return len(all_answers)

    def insert_user_all_answers(self, user_id: str):
        change_user_status(db=self.db, user_id=user_id, status=FLAG.IN_USE)

        answer_page_count, answer_page_base, answer_list_soup = self.first_answer_page(user_id=user_id)
        self.insert_answer_list_page(answer_list_soup, user_id)

        # insert all others, if any
        answers = 20
        if answer_page_count > 1:
            page_range = range(2, answer_page_count + 1)
            for page_num in page_range:
                current_page_link = answer_page_base + "?page=" + str(page_num)
                r = self.session.get(current_page_link)
                soup = BeautifulSoup(r.content.decode('utf-8'), BS_PARSER)
                answers += self.insert_answer_list_page(soup, user_id)

        change_user_status(db=self.db, user_id=user_id, status=FLAG.FINISHED)
        log.info("Inserted {} answers for user {}.".format(answers, user_id))

    # Start from single Question page
    # - all answers
    # - new users

    def update_question_detail(self, soup_content, question_id):
        title = soup_content.find(Magic.Question.title).get_text().strip()
        detail = soup_content.find('div', class_=Magic.Question.question_detail).get_text().strip()
        follower = int(soup_content.find('div', class_=Magic.Question.follower).a.get_text())
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
            author_temp = str(bs_answer.find('a', class_=Magic.Question.author_div))
            author = Magic.Question.author_name.findall(author_temp)[0]
        except IndexError:
            author = 'Anonymous'

        try:
            comment_div = str(bs_answer.find('a', class_=Magic.Question.comment_div))
            comments_count = int(Magic.number.findall(comment_div)[0])
        except IndexError:
            # no comments yet
            comments_count = 0

        return author, comments_count, content

    def update_question_insert_answer(self, question_id):
        change_question_status(db=self.db, question_id=question_id, status=FLAG.IN_USE)
        log.info("Updating untouched question {}".format(question_id))

        # Update question detail
        question_url = 'http://www.zhihu.com/question/' + str(question_id)
        question_content = self.session.get(question_url).content.decode('utf-8')

        q_soup = BeautifulSoup(question_content, BS_PARSER)
        if type(q_soup.find(Magic.Question.title)) is not None:
            self.update_question_detail(q_soup, question_id)
        else:
            return  # 404

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

        change_question_status(db=self.db, question_id=question_id, status=FLAG.FINISHED)

    def fetch_users(self):
        untouched_user_list = get_user_cursor(self.db, EXPLORE_USER_COUNT)
        for user in untouched_user_list:
            user = user["user_id"]
            self.insert_user_all_answers(user)

        log.info("Finished crawling {} users.".format(len(EXPLORE_USER_COUNT)))

    def fetch_questions(self):
        questions_list_cursor = get_untouched_question_cursor(self.db, EXPLORE_QUESTION_COUNT)
        for question_item in questions_list_cursor:
            question = question_item['question_id']
            self.update_question_insert_answer(question)

        log.info("Finished crawling {} questions.".format(EXPLORE_QUESTION_COUNT))

        # Multi processing version
        # pool = ThreadPool(CONCURRENCY)
        # question_list = [question['question_id'] for question in questions_list_cursor]
        # _ = pool.map(self.update_question_insert_answer, questions_list)
        # pool.close()
        # pool.join()

    def run(self):

        # reset all unfinished user/questions
        self.db.answers.update_many({'touched': FLAG.IN_USE}, {'$set': {'touched': FLAG.UNTOUCHED}})
        self.db.users.update_many({'touched': FLAG.IN_USE}, {'$set': {'touched': FLAG.UNTOUCHED}})

        while True:
            # self.fetch_users()
            self.fetch_questions()

if __name__ == "__main__":
    crawler = Crawler()
    crawler.run()
