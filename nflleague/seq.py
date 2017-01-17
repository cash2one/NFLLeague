import nflleague
import nflgame
import functools
import itertools
import operator

class GenPlayer(nflgame.seq.Gen):
    def __init__(self,iterable):
        super(GenPlayer,self).__init__(iterable)
    
    def sort(self,field,descending=True):
        def islambda(var):
            lam=lambda:0
            return isinstance(var,type(lam)) and var.__name__ == lam.__name__
        def attrget(item):
            return getattr(item,field,0)
        
        return self.__class__(sorted(self,reverse=descending,key=field if islambda(field) else getattr))
    def remove(self,pid):
        return self.__class__(itertools.ifilter(lambda x:x.player_id!=pid,self))
    def add(self,obj):
        return self.__class__(list(self)+[obj])

