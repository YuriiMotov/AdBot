from sqlalchemy import select
from sqlalchemy.orm import Session

from db import models as m


# TODO:
# - Add min time interval between cache updates
# - make it iterable


class KeywordsCache():
    def __init__(self):
        self._cache = {}
        self._update_required = True
    
    def get_keywords(self, session: Session):
        if not self._update_required:
            return self._cache
        else:
            self._cache = {}
            st = select(m.Keyword).join(m.User, m.Keyword.users).where(m.User.forwarding == True)
            for kw in session.scalars(st).all():
                self._cache[kw.word] = [user.id for user in kw.users]
            self._update_required = False
            return self._cache
    
    def request_update(self):
        self._update_required = True



keywords_cached = KeywordsCache()
