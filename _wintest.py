import tkinter as tk, ctypes
u=ctypes.windll.user32
root=tk.Tk(); root.overrideredirect(True); root.attributes('-topmost',True)
root.geometry('320x420+40+200'); root.configure(bg='#11161c')
c=tk.Canvas(root,width=320,height=420,bg='#11161c',highlightthickness=0); c.pack()
c.create_rectangle(6,6,314,414,outline='#ffd23f',width=3)
c.create_text(160,40,text='SMALL WINDOW TEST',fill='#ffd23f',font=('Segoe UI',16,'bold'))
c.create_text(160,90,text='If you see this box on the LEFT\nover the game, multi-window\nis the fix.',fill='#fff',font=('Segoe UI',11),justify='center')
def style():
    h=u.GetAncestor(root.winfo_id(),2); ex=u.GetWindowLongW(h,-20)
    u.SetWindowLongW(h,-20, ex|0x80|0x8000000)  # toolwindow|noactivate (like toggle, NOT click-through)
    u.SetWindowPos(h,-1,0,0,0,0,0x1|0x2|0x10)
root.after(80,style); root.after(20000,root.destroy); root.mainloop()
