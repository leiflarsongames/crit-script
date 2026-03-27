from kivy.app import App
from kivy.uix.button import Button

class SimpleButtonApp(App):
    def build(self):
        b = Button(text='Push Me!')
        return b

if __name__ == '__main__':
    SimpleButtonApp().run()