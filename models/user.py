from flask_login import UserMixin


class User(UserMixin):
    def __init__(self, id, username, email, active_character_id=None):
        self.id = id
        self.username = username
        self.email = email
        self.active_character_id = active_character_id

    def get_id(self):
        return str(self.id) 