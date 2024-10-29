from tkinter import filedialog
import socket
import errno
import sys
import subprocess
from options import *
import os
import json
import pickle

HEADER_LENGTH = 10

# downloading additional imports
try:
    import customtkinter as ctk # type: ignore
    import thread # type: ignore
    import keyboard
    from PIL import Image
except Exception:
    subprocess.Popen(["pip", "install", "-r", "requirements.txt"])
    import customtkinter as ctk # type: ignore
    import thread # type: ignore
    import keyboard
    from PIL import Image
    
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS2
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class App(ctk.CTk):
    def __init__(self):
        
        super().__init__(fg_color='#ccacab')
        
        self.title('Chatroom!')

        x = 800
        y = 800

        x_offset = int((self.winfo_screenwidth() / 2) - x/2)
        y_offset = int((self.winfo_screenheight() / 2) - x/2)

        self.geometry(f'{x}x{y}+{x_offset}+{y_offset}')

        self.minsize(600,700)
        self.update_idletasks()

        self.usernameCheck()

        self.establishConnection()

        self.chatFrame = ChatFrame(self)

        background = thread.Thread(target=self.startBackground)
        background.start() 

        self.after(20, lambda: self.chatFrame.inputField.focus())

        self.mainloop()
    
    def usernameCheck(self):
        try:
            file = open("data.txt", "r")
        except FileNotFoundError:
            file = open("data.txt", "x")
            json.dump({},file)
            file = open("data.txt","r")

        if file != {}: data = json.load(file)

        if "username" in data:
            self.my_username = data["username"]
        else:
            UsernamePopup(self)
        
        file.close()

    def establishConnection(self):
        
        IP = "127.0.0.1"
        PORT = 9191

        self.HEADER_LENGTH = 10

        # Create a socket
        # socket.AF_INET - address family, IPv4, some otehr possible are AF_INET6, AF_BLUETOOTH, AF_UNIX
        # socket.SOCK_STREAM - TCP, conection-based, socket.SOCK_DGRAM - UDP, connectionless, datagrams, socket.SOCK_RAW - raw IP packets
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            # Connect to a given ip and port
            self.after(1000, self.client_socket.connect((IP, PORT)))
        except Exception:
            try: 
                self.connToken = "tinychatroom"
                #subprocess.run(["zrok", "access", "private", self.connToken])
                subprocess.Popen(["zrok", "access", "private", self.connToken])

                self.after(1000, self.client_socket.connect((IP, PORT)))
            except Exception:
                subprocess.Popen(["zrok", "enable", "Kqs11S96zRq8"])

        # Set connection to non-blocking state, so .recv() call won;t block, just return some exception we'll handle
        self.client_socket.setblocking(False)

        # Prepare username and header and send them
        # We need to encode username to bytes, then count number of bytes and prepare header of fixed size, that we encode to bytes as well
        username = self.my_username.encode('utf-8')
        username_header = f"{len(username):<{self.HEADER_LENGTH}}".encode('utf-8')
        self.client_socket.send(username_header + username)

    def startBackground(self):
            try:
                # Now we want to loop over received messages (there might be more than one) and print them
                while True:
                    # Receive our "header" containing username length, it's size is defined and constant
                    username_header = self.client_socket.recv(self.HEADER_LENGTH)

                    # If we received no data, server gracefully closed a connection, for example using socket.close() or socket.shutdown(socket.SHUT_RDWR)
                    if not len(username_header):
                        print('Connection closed by the server')
                        sys.exit()

                    # Convert header to int value
                    username_length = int(username_header.decode('utf-8').strip())

                    # Receive and decode username
                    username = self.client_socket.recv(username_length).decode('utf-8')

                    message_header = self.client_socket.recv(self.HEADER_LENGTH)
                    message_length = int(message_header.decode('utf-8').strip())

                    if username == "server":
                        message = pickle.loads(self.client_socket.recv(message_length))
                        
                        self.loadData(message)
                    else:
                        # Now do the same for message (as we received username, we received whole message, there's no need to check if it has any length)
                        message = self.client_socket.recv(message_length).decode('utf-8')

                        self.chatFrame.addMessage(message, 'msg_received', username)
                    

            except IOError as e:
                # This is normal on non blocking connections - when there are no incoming data error is going to be raised
                # Some operating systems will indicate that using AGAIN, and some using WOULDBLOCK error code
                # We are going to check for both - if one of them - that's expected, means no incoming data, continue as normal
                # If we got different error code - something happened
                if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                    print('Reading error: {}'.format(str(e)))
                    sys.exit()

            App.after(self, 1000, self.startBackground)

    def loadData(self, data):
        for block in data:
            msgtype = 'msg_sent' if block["user"] == self.my_username else 'msg_received'
            self.chatFrame.addMessage(block["message"], msgtype, block["user"])

class ChatFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color='#ccacab')
        self.parent = parent

        self.username = parent.my_username
        self.w_height = parent.winfo_height()
        self.generateChatField()
        self.generateInputField()

        self.pack(side='right', expand=True, fill='both')

    def addMessage(self, message, msgType, username):
        Message(self, message, msgType, username)
        # Sticks to the bottom if already at the bottom
        if(self.chatFrame._scrollbar.get()[1] > 0.9):
            self.after(1, lambda: self.chatFrame._parent_canvas.yview_moveto(1))
    
    def generateChatField(self):
        self.chatFrame = ctk.CTkScrollableFrame(self, fg_color='#ccacab')
        self.chatFrame.pack(expand=True, fill='both')

        self.chatFrame._parent_canvas.configure(xscrollincrement= 1000)

    def generateInputField(self):
        frame = ctk.CTkFrame(self, fg_color='#ccacab')

        sendButton = ctk.CTkButton(frame,text='+', width=50, height=50, corner_radius=10, fg_color='#333333', font = ('Bahnschrift', 24), text_color= '#ebf1ff', command=self.open_file_dialog)
        sendButton.pack(side='right', pady=10, padx=10)

        self.inputField = ctk.CTkTextbox(frame, corner_radius=15, height=62, font = ('Bahnschrift', 24), fg_color='#333333', wrap='word')
        self.inputField.pack(side='left', expand='true', fill='both', padx=10, pady=5)
        
        self.inputFieldHeight = self.inputField.cget('height')
        self.curr_row = 1

        self.inputField.bind('<KeyPress-Return>', self.returnPressed)
        self.inputField._textbox.bind('<Key>', self.reset_height)

        # had to do this, not sure why it doesnt work otherwise
        self.returnPressed()

        image = Image.open(resource_path('images\\sendbtn.png'))
        image_tk = ctk.CTkImage(image, size=(30,30))
        sendButton = ctk.CTkButton(frame,text='', image=image_tk, width=50, height=50, corner_radius=10, fg_color='#333333', command=self.sendMsg)
        sendButton.pack(side='right', pady=10, padx=10)

        frame.pack(fill='both')
    
    def reset_height(self, event):
        height = self.inputField._textbox.tk.call((self.inputField._textbox._w, "count", "-update", "-displaylines", "1.0", "end"))
        if(height != 1):
            self.inputField.configure(height=63 + (height-1)*32)
        elif(event.keysym == 'BackSpace'):
            self.inputField.configure(height=63)

    '''
    def wrapChecker(self, event):
        charLength = len(self.inputField.get(f'{self.curr_row}.0', f'{self.curr_row}.end'))
        wrapLength = 20
        buildUp = 0
        while True:
            if (charLength >= buildUp + wrapLength):
                # thread.Thread(target= lambda: self.inputHeightAnimation(32)).start() 
                self.inputField.configure(height= self.inputField.cget('height') + 32)
                self.curr_row += 1
                buildUp += wrapLength
    '''

    def sendMsg(self):
        if(self.inputField.get(1.0, 'end') != '\n'):
            message = list(self.inputField.get(1.0, 'end'))
            message[len(message)-1] = ''
            message = ''.join(message).encode('utf-8')
            message_header = f"{len(message):<{self.parent.HEADER_LENGTH}}".encode('utf-8')
            self.parent.client_socket.send(message_header + message)
            Message(self, message.decode('utf-8'), 'msg_sent', self.username)
            self.inputField.delete(1.0, 'end')

            # Sticks to the bottom if already at the bottom
            if(self.chatFrame._scrollbar.get()[1] > 0.9):
                self.after(5, lambda: self.chatFrame._parent_canvas.yview_moveto(1))
                
    def returnPressed(self, *kwargs):
        if(keyboard.is_pressed('shift') == False):
            self.sendMsg()
            self.curr_row = 1
            self.inputField.configure(height=self.inputFieldHeight)
            self.after(2, lambda: self.inputField.delete(1.0, 'end'))
        elif (keyboard.is_pressed('shift')):
            #thread.Thread(target= lambda: self.inputHeightAnimation(32)).start()
            self.inputField.configure(height= self.inputField.cget('height') + 32)
            self.curr_row += 1
    
    '''
    def inputHeightAnimation(self, increment):
        outlier = increment % 2
        initial_height = self.inputField.cget('height')
        for i in range(1,3):
            self.after(1, self.inputField.configure(height= initial_height + i*floor(increment/2)))
        self.inputField.configure(height= self.inputField.cget('height') + outlier)
    '''

    def open_file_dialog(self):
        image_paths = filedialog.askopenfilenames(title="Images", filetypes=[("Image files", "*.jpg *.jpeg *.png"), ("All files", "*.*")])
        for image_path in image_paths:
            pass
        
class Message(ctk.CTkFrame):
    def __init__(self, parent, message, msgType, username):
        super().__init__(parent.chatFrame, fg_color='#ccacab')

        self.columnconfigure((1,2), uniform='a', weight=1)
        self.rowconfigure(1, uniform='a', weight=1)
        
        pFrame = ctk.CTkFrame(self, fg_color='#ccacab')

        pfp = ctk.CTkLabel(pFrame, text = '', corner_radius= 5, width=20, height=20, fg_color='#FFFFFF')
        pfp.pack(side=PACKING[msgType]['side'],ipady=10, ipadx=10, pady=20, padx=5, anchor='n')
        
        msgFrame = ctk.CTkFrame(pFrame, fg_color='#333333', corner_radius= 10)

        userField = ctk.CTkLabel(msgFrame, text = username, wraplength=300, justify=JUSTIFY[msgType]['user'], font=('Bahnschrift', 14), text_color=COLORS[msgType]['user'])
        userField.pack(side='top', pady=1, padx=12, anchor=PACKING[msgType]['user_anchor'])
        
        msgField = ctk.CTkLabel(msgFrame, text = message, wraplength=300, justify=JUSTIFY[msgType]['msg'], font=('Bahnschrift', 18), text_color=COLORS[msgType]['msg'])
        msgField.pack(side='top', pady=1, padx=10, anchor=PACKING[msgType]['msg_anchor'])

        msgFrame.pack(side=PACKING[msgType]['side'], ipady=5, padx=5, pady=2)
        
        pFrame.grid(row=1, column=COLUMN[msgType], sticky='nsew')
            
        
        self.pack(fill='x', pady=2)

class popup(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent, fg_color='#333333')

        x = parent.winfo_x()
        y = parent.winfo_y()
        x_offset = int((parent.winfo_width() / 2) - 200)
        y_offset = int((parent.winfo_height() / 2) - 100)

        self.geometry(f'400x200+{x+x_offset}+{y+y_offset}')

        '''
        image = Image.open('Images/main page/18+.png')
        image_tk = ctk.CTkImage(image, size=(60,60))
        image_label = ctk.CTkLabel(self, image=image_tk, text="")
        image_label.pack(pady=20)
        '''
        label = ctk.CTkLabel(self, text="The server has been reset, please re-enter the token number below.", font = ('Bahnschrift', 18))
        label.pack(pady=10)

        label = ctk.CTkEntry(self, font = ('Bahnschrift', 18))
        label.pack(pady=10)

        yes_button = ctk.CTkButton(self, text='Submit', command = self.submit, font = ('Bahnschrift', 18), fg_color='#492338')
        yes_button.pack(pady=10)

        self.transient(parent) 
        self.grab_set() 
        parent.wait_window(self) 
    
    def submit(self):

        self.destroy

class UsernamePopup(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent, fg_color='#333333')

        x = parent.winfo_x()
        y = parent.winfo_y()
        x_offset = int((parent.winfo_screenwidth() / 2) - 200)
        y_offset = int((parent.winfo_screenheight() / 2) - 100)

        self.geometry(f'400x200+{x+x_offset}+{y+y_offset}')

        label = ctk.CTkLabel(self, text="Please enter a username.", font = ('Bahnschrift', 18))
        label.pack(pady=10)

        self.label = ctk.CTkEntry(self, font = ('Bahnschrift', 18))
        self.label.pack(pady=10)

        yes_button = ctk.CTkButton(self, text='Submit', command = self.submit, font = ('Bahnschrift', 18), fg_color='#492338')
        yes_button.pack(pady=10)

        self.transient(parent) 
        self.grab_set() 
        parent.wait_window(self) 
    
    def submit(self):
        if not (self.label.get() == "server"):
            save("username", self.label.get())
            self.destroy()

def save(header:str, _data):
    
    file = open("data.txt", "r")
    data = json.load(file)
    data[header] = _data

    file = open("data.txt", "w")
    json.dump(data,file)

    file.close()

if __name__ == "__main__":
    App()