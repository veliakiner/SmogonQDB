from random import randrange
from itertools import permutations

#Select a random list of listlength elements from iterable list
#if no listlength given, it automatically gives a list the same length as the iterable


def random_list(iterable,listlength='none given'):
    if listlength=='none given':
        listlength=len(iterable)
    if listlength>len(iterable): #makes sure that the shuffled list length doesn't exceed the
                                 #input list (since no duplicate items are allowed)
        listlength=len(iterable)
    randomlist=[]
    while len(randomlist)<listlength: #adds to randomlist while removing from the input list
                                      #until it is the desired size
        item=iterable[randrange(len(iterable))]
        iterable.remove(item)
        randomlist.append(item)
    return randomlist


#test case
#for i in range(10):
#    print random_list([1,2,3,4,5,6,7,8,9,10])
