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
        
        return self.__class__(sorted(self,reverse=descending,key=field if islambda(field) else attrget))
    
    def remove(self,pid):
        return self.__class__(self.filter(player_id=lambda x:x!=pid)) 
    
    def add(self,obj):
        return self.__class__(list(self)+[obj])

#Class for managing instances of individual player on different season and weeks
class SeqPlayer(GenPlayer):
    def __init__(self,iterable):
        super(GenPlayer,self).__init__(iterable)
        
