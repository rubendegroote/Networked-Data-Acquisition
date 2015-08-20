# from collections import OrderedDict
import json

# def stamp(name):
#     def dec(func):
#         def func_wrapper(self,message):
#             try:
#                 self.counter += 1
#             except:
#                 self.counter = 0
#             if 'mes' in message.keys():
#                 message['counter'+name] = self.counter
#             else:
#                 m = OrderedDict()
#                 m['mes'] = message
#                 m['counter'+name] = self.counter
#             return func(self,m)
#         return func_wrapper
#     return dec



# class Ob(object):
#     def onclicK(self):
#         #message = get_stuff_from_GUI
#         # self.send(message)
#         pass

#     @stamp('hoipipeloi')
#     def send(self, message):
#         # socket.push(message)
#         print('performed that')
#         print(message)
#         return message

# class Ob2(object):
#     @stamp('yoohoo')
#     def send(self,message):
#         return message


# o = Ob()
# o2 = Ob2()

# mes = o.send(message = {'op':'do','args':[1]})
# # mes = o2.send(message = mes)
# # for key,val in mes.items():
# #     print(key,val)

# print(mes)
# print(json.loads(json.dumps(mes)))
# print(json.dumps(str(b'hello')))
# a = {'a': 1}
# b = a
# b['a'] = 2
# print(a)

# from backend.Helpers import *

# class Ob(object):

#     def __init__(self):
#         self.name = 'test'

#     @track
#     def generate_message(self, message):
#         print(message)
#         return json.loads(message)

# a = Ob()
# message = json.dumps({'message': {'op': 'subtract', 'parameters': [0]}})
# params = {'value': [1]}
# message = add_reply(message, params)
# print(message)
# a.generate_message(a.generate_message(message))
print(json.dumps(None))