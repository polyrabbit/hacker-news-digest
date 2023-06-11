import time

ACCESS = 'access'


class DictCache(dict):

    def mark_accessed(self):
        super(DictCache, self).__setitem__(ACCESS, int(time.time()))

    def expired(self, ttl):
        if ACCESS not in self:
            return True
        return super(DictCache, self).__getitem__(ACCESS) + ttl < time.time()
