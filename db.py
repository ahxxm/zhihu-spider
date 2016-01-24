import pymongo

from settings import DB_PORT, DB_HOST

client = pymongo.MongoClient(DB_HOST, DB_PORT)
db_client = client.Zhihu


class FLAG:

    UNTOUCHED = 0
    FINISHED = 1
    IN_USE = 2


def get_user_cursor(db, count) -> pymongo.cursor.Cursor:
    cursor = db.users.find({'touched': FLAG.UNTOUCHED}).limit(count)
    return cursor


def get_untouched_question_cursor(db, count) -> pymongo.cursor.Cursor:
    cursor = db.questions.find({'touched': FLAG.UNTOUCHED}).limit(count)
    return cursor


def insert_new_question(db, question_id):
    if db.questions.find({'question_id': question_id}).count() == 0:
        db.questions.insert_one({'question_id': question_id, 'touched': FLAG.UNTOUCHED})


def change_question_status(db, question_id, status):
    db.questions.update_one({'question_id': int(question_id)}, {'$set': {'touched': status}})


def insert_new_user(db, user_id):
    if db.users.find({'user_id': user_id}).count() == 0:
        db.users.insert_one({'user_id': user_id, 'touched': FLAG.UNTOUCHED})


def change_user_status(db, user_id: str, status):
    db.users.update_one({'user_id': user_id}, {'$set':{'touched': status}})


def insert_answer(db, answer_id, author, question_id, comments_count, content):
    if db.answers.find({'answer_id': answer_id}).count() == 0:
        db.answers.insert_one({'answer_id': answer_id,
                               'author': author,
                               'relate_question': question_id,
                               'comments_count': comments_count,
                               'content': content})
