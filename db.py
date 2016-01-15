from pymongo import MongoClient

from .settings import DB_PORT, DB_HOST

client = MongoClient(DB_HOST, DB_PORT)
db_client = client.Zhihu


class FLAG:

    UNTOUCHED = 0
    FINISHED = 1
    IN_USE = 2


def get_user_list(db, user_count) -> list:
    users_list = list(db.users.find({'touched': FLAG.UNTOUCHED}).limit(user_count))
    users_list = [str(user['user_id']) for user in users_list]
    return users_list


def get_untouched_questions(db, count):
    questions_list = list(db.questions.find({'touched': FLAG.UNTOUCHED}).limit(count))
    question_list = [str(question['question_id']) for question in questions_list]
    return question_list


def insert_new_question(db, question_id):
    if db.questions.find({'question_id': question_id}).count() == 0:
        db.questions.save({'question_id': question_id, 'touched': FLAG.UNTOUCHED})


def insert_new_user(db, user_id):
    if db.users.find({'user_id': user_id}).count() == 0:
        db.users.save({'user_id': user_id, 'touched': FLAG.UNTOUCHED})


def insert_answer(db, answer_id, author, question_id, comments_count, content):
    if db.answers.find({'answer_id': answer_id}).count() == 0:
        db.answers.save({'answer_id': answer_id,
                         'author': author,
                         'relate_question': question_id,
                         'comments_count': comments_count,
                         'content': content})
