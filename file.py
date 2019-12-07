from datetime import datetime
my_int=55
with open("/home/preetham/log.txt", 'a') as file:
    file.write('The value at: %s is %d\n' %(datetime.now(), my_int))
file.close()
