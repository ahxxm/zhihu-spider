import re

BS_PARSER = "lxml"


class Magic:

    hyperlink = "a"
    harmony_answer = "naive"
    seed_user = "zhang-jia-wei"

    number = re.compile("\d+")
    answer_id_in_answer = re.compile("(?<=answer\/)\d+")

    class UserProfile:

        answer = "zm-item"
        answer_paginator = "zm-invite-pager"
        answer_content_class_in_user_profile = "content hidden"
        comments_count = " meta-item toggle-comment"
        question = "question_link"

        question_id_in_user_profile = re.compile("(?<=question\/)\d+")

    class Question:

        follower = "zg-gray-normal"
        title = "h2"
        question_detail = "zm-editable-content"
        answer_div = "zm-item-answer  zm-item-expanded"
        answer_content_div = "zm-editable-content clearfix"
        author_div = "author-link"
        author_name = re.compile('(?<=people\/).*?(?=\"\>)')
        comment_div = " meta-item toggle-comment"
        mentioned_userid = re.compile('(?<=\/people\/).*?(?=\")')
