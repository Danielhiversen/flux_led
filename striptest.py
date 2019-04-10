import flux_led as flux
import re

printnonl = lambda s : print(s, end='')
answers = []

def assertion(f, msg):
    printnonl(msg)
    if (f):
        print("yes")
    else:
        print("no")
        exit()

def askyesno(str, index):
    answer = input(str+' (Y/n) ')
    if answer[0].lower() == 'n':
        answers.append([index, 0])
    else:
        answers.append([index, 1])

print("Thank you for doing the testing of Magic Home RGB strip controllers.")
print("Before starting, please open the Magic Home App and look how your strip setup is for checking.")
ipaddress = input("Please enter the ip address of the strip controller: ")
while re.match("^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$", ipaddress) is None:
    print("Wrong IP Adress")
    ipaddress = input("Please enter the ip address of the strip controller: ")

controller = flux.WifiLedBulb(ipaddress)
assertion(controller.connect(2), "Checking whether connection to controller works... ")

assertion(controller.stripprotocol == True, "Checking whether controller is a strip controller... ")

stripdata = controller.query_strip_state()
assertion(stripdata != False, "Checking if the strip controller status can be received... ")

assertion(stripdata[0] == 0x63, "Checking whether the strip setup data can be understood... ")

led_count = stripdata[1] << 8 + stripdata[2]
try:
    ic = flux.StripIC(stripdata[3:10])
except:
    ic = None
assertion(ic is not None, "Checking whether the strip IC value can be understood... ")

try:
    wiring = flux.StripWiring(stripdata[10])
except:
    wiring = None
assertion(wiring is not None, "Checking whether the strip wiring value can be understood... ")

askyesno("Is the LED count = "+led_count+"?", 0)
askyesno("Is the strip IC = "+ic.name+"?", 1)
askyesno("Is the strip wiring = "+wiring.name+"?", 2)
assertion(all(item[1] == 1 for item in answers), "Checking whether values are recognized correctly... ")

print("Now it will be tested whether the communication with the strip controller works...")
state = 'on' if controller.isOn() else 'off'
askyesno("Is the controller currently "+state+"?", 3)
if (state == 'off' and answers[3][1] == 1) or (state == 'on' and answers[3][1] == 0):
    controller.turnOn()
    controller.update_state()
    state = 'on' if controller.isOn() else 'off'
    askyesno("Is the controller now "+state+"?", 4)
    assertion(answers[4][1] == 1, "Checking whether the on/off state is recognized correctly... ")
controller.setRgb(255, 0, 0)
askyesno("Is the light now red?", 5)
if answers[5][1] == 0:
    controller.setRgb(255, 255, 0)
    askyesno("Is the light now light blue?", 6)
    if answers[6][1] == 0:
        print("Communication error")
    else:
        print("Wrong wiring set")
else:
    controller.setRgb(0, 255, 0)
    askyesno("Is the light now green?", 7)
    if answers[7][1] == 0:
        controller.setRgb(255, 255, 0)
        askyesno("Is the light now magenta?", 8)
        if answers[8][1] == 0:
            print("Communication error")
        else:
            print("Wrong wiring set")
    else:
        controller.setRgb(0, 0, 255)
        askyesno("Is the light now blue?", 9)
        if answers[9][1] == 0:
            print("Communication error")
