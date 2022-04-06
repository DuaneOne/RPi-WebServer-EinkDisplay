"""
This script executes on a RPi Zero-W with a 2.13 eink display.   This scipt serves up a web page accessable from a
browser on my network at 192.168.1.42:4545 
This script provides a way to change the eink display text.  Power can then be removed from the RPi and the
display will retain the text.  This script is short, thanks to good scripts for the web and e-ink display (see imports).
The sleep statements were added because sometimes during early debugging, the values would not load completely.
sometimes the last text would be missing or wrong color, etc.  May not be necessary now, but I left them in.
          --- Duane March 2022

   Three ways to run the script:
   python3 myEinkWeb.py
             or
   nohup python3 -u myEinkWeb.py &
   after that you can quit ssh and when you go in again, you can find the file nohup.out that contains the output.
             or
    http://www.diegoacuna.me/how-to-run-a-script-as-a-service-in-raspberry-pi-raspbian-jessie/
   This service will restart the myEinkWeb.py script if it ever stops.
   The service file created for myEinkWeb.py is   /etc/systemd/system/myEinkWeb.service
          sudo  mv myEinkWeb.service /etc/systemd/system/myEinkWeb.service
          sudo chown pi:pi /etc/systemd/system/myEinkWeb.service    # changes user and group to pi
          sudo  chmod  644  /etc/systemd/system/myEinkWeb.service

          sudo systemctl daemon-reload
          sudo systemctl enable myEinkWeb.service

         sudo systemctl status myEinkWeb.service
         sudo systemctl stop myEinkWeb.service
         sudo systemctl start myEinkWeb.service

   print statements and errors output to   /var/log/syslog
   as well as /var/log/daemon.log  

   ps aux    to list processes running     kill [the number in left column for python3]
"""


import os
import json   #  for file reads and writes format
import time
import PySimpleGUIWeb as sg    #  for web interface
import epd2in13b               # for e-ink display
from PIL import Image          # for Preview output in browser
from PIL import ImageFont
from PIL import ImageDraw


def main():
    WEB_PORT = 4545         # this can be changed easily
    epd = epd2in13b.EPD()    # for e-ink display
    epd.init()

    RBG_RED = (255, 0, 0)
    RBG_BLACK = (0, 0, 0)
    RBG_WHITE = (255, 255, 255)
    fontSizeList = (52,48,44,40,36,32,28,24,20,16,12)       #  for web, last value becomes the default value
    my_wd = os.path.dirname(os.path.realpath(__file__)) + '/saved'     #  working directory for saved values

    font_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'arial.ttf')
    preview_image_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'preview_image.png')

    INPUT_LINE_COUNT = 12     # number of text lines for user input
    INPUT_COLUMNS = 3         # input test, font size, font color
    orient = 'portrait'      # default display orientation

    if not os.path.isdir(my_wd):
        os.mkdir(my_wd)
    savedFileList = [f for f in os.listdir(my_wd)]

    input_controls = []     #  text boxes for user input
    for i in range(0, INPUT_LINE_COUNT):
        input_controls.append([sg.Input(size=(30, 1)), sg.InputCombo(fontSizeList, size=(5, 1), enable_events=True),
                               sg.InputCombo(("red", "black"), size=(6, 1), enable_events=True)])

    layout = [
        [sg.Text('Type in text for each line of the eink display or Load saved text.')],
        *input_controls,
        [sg.Button('Preview'), sg.InputCombo(("landscape", "portrait"), key='-ORIENT-', size=(9, 1), enable_events=True), sg.Button('Debug')],
		[sg.Image(key='-OUT1-')],
        [sg.Text('Transfer text to eink display: '), sg.Button('Transfer')],
        [sg.Text('Text inputs will be saved in RPi folder  ' + my_wd)],
        [sg.Input("type_filename", key='-SAT-', size=(30, 1)), sg.Button('Save')],
        [sg.InputCombo(savedFileList, key='-SAL-'), sg.Button('Load'), sg.Button('Delete')],
        [sg.Quit(), sg.Button('ReBootRPi'), sg.Button('UnplugRPi')],
    ]
    window = sg.Window('eink editor..',layout, finalize=True, web_port=WEB_PORT)
    needToProcessPreviewAgain = False


    while True:
        event, values = window.read(timeout=10)         # mS
        if event is None or event in (sg.WIN_CLOSED, 'Quit'):
            break

        if event == 'Preview' or (event == sg.TIMEOUT_KEY  and needToProcessPreviewAgain ):
            #     values looks like this for content
            #     {0: 'line1 text', 1: '8', 2: 'black', 3: 'line2 text', 4: '8', 5: 'black', 6: '', 7: '8', 8: 'black', 9: '', 10: '8', 11: 'black', 12: '', ...}
            #   Copy each input line text to output line, formatted for size and color
            try:
                image = Image.new('RGB', (epd.width, epd.height), color=RBG_WHITE)
                draw = ImageDraw.Draw(image)

                # This is similar to the Transfer Logic below
                # use all the input_controls fields.  keys are int, values are str.  step every row
                x = 2; y = 2  # top left coordinated for display
                for i in range(0, INPUT_LINE_COUNT * INPUT_COLUMNS, INPUT_COLUMNS):
                    fSize = int(values[i + 1])  #
                    font = ImageFont.truetype(font_path, fSize)  # second param is font size
                    if values[i + 2] == 'black':
                        draw.text((x, y), values[i], font=font, fill=RBG_BLACK)
                    elif values[i + 2] == 'red':
                        draw.text((x, y), values[i], font=font, fill=RBG_RED)
                    y = y + fSize    # spacing in y direction for next display line

                image.save(preview_image_path, "PNG")

            except Exception as e:
                print("Error encountered when trying to generate the perview image: {}".format(preview_image_path))
                print("Exception: \n {}".format(str(e)))
                os._exit(1)

            window['-OUT1-'].update(filename=preview_image_path)
            needToProcessPreviewAgain = False  # only set to True by Load and Orient

        if event == 'Save':
            if values['-SAT-'] is not None:
                savedFileName = my_wd + '/' + values['-SAT-']
                savedFileList = [f for f in os.listdir(my_wd)]
                jsonValues = json.dumps(values)    #  convert values dict to json
                f = open(savedFileName, "w")
                f.write(jsonValues)
                time.sleep(0.01)
                f.close()
                time.sleep(0.01)
                savedFileList = [f for f in os.listdir(my_wd)]
                window['-SAL-'].update(values=savedFileList) ; time.sleep(0.01)       # updates the list
                window.refresh() ;  time.sleep(0.01) # otherwise


        if event == 'Load':     #  loads the input text boxes (input_controls)
            savedFileList = [f for f in os.listdir(my_wd)]
            if savedFileList is not None and values['-SAL-'] is not None:
                savedFileName = my_wd + '/' + values['-SAL-']
                if os.path.isfile(savedFileName):
                    f = open(savedFileName, "r")
                    jsonValues = f.read()
                    time.sleep(0.01)
                    dictVal = json.loads(jsonValues)   #  convert to dictionary
                    f.close()
                    time.sleep(0.01)
                    #  Note dict keys from json keys are all strings, whereas original keys can be int
                    for i in range (0,INPUT_LINE_COUNT * INPUT_COLUMNS):        # populate all the input_controls fields.
                        try:
                            window[i].update(dictVal[str(i)]) ; time.sleep(0.01)   # window[0].update(dictVal['0'])
                        except:
                            break     # stop input text boxes updates on any error
                    window.refresh() ;  time.sleep(0.01) # otherwise
                    needToProcessPreviewAgain = True   #  this works to populate output lines  since Preview is above here


        if event == 'Delete':
            savedFileList = [f for f in os.listdir(my_wd)]
            if savedFileList is not None and values['-SAL-'] is not None:
                savedFileName = my_wd + '/' + values['-SAL-']
                if os.path.isfile(savedFileName):
                    os.remove(savedFileName)
                    time.sleep(0.01)
                    savedFileList = [f for f in os.listdir(my_wd)]
                    time.sleep(0.01)
                    # print("savedFileList_S ", savedFileList)
                    window['-SAL-'].update(values=savedFileList) ; time.sleep(0.01)  # updates the list
                    window.refresh() ;  time.sleep(0.01) # otherwise


        if event == 'Transfer':    # to the e-ink display
            # clear the e-ink frame buffer (init all frame to FF hex). for python 3.5
            #frame_black = [0xFF] * int(display_width * display_height / 8)
            #rame_red = [0xFF] * int(display_width * display_height / 8)
            frame_black = [0xFF] * int(epd.width * epd.height / 8)
            frame_red = [0xFF] * int(epd.width * epd.height / 8)
            # in portait mode, the upper left is 1,1.  upper right is 104,1.  lower left is 1,212.   lower right is 104,212.
            # write strings to the buffer.  note the text truncates at the end of the physical diaplay and does not auto=wrap to next line
            #  max of 14 chars at size 12 font in portrait mode.

            # This is similar to the Preview Logic above.
            # use all the input_controls fields.  keys are int, values are str.  step every row
            x = 2; y = 2      # top left coordinated for display
            for i in range(0, INPUT_LINE_COUNT * INPUT_COLUMNS, INPUT_COLUMNS):
                fSize = int(values[i+1])
                font = ImageFont.truetype(font_path, fSize)  # second param is font size
                if values[i+2] == 'black':
                    epd.draw_string_at(frame_black, x, y, values[i], font, 1)   # last param = 1 means use color display
                elif values[i+2] == 'red':
                    epd.draw_string_at(frame_red, x, y, values[i], font, 1)  #
                y = y + fSize         # spacing in y direction for next line
            epd.display_frame(frame_black, frame_red)  # the first frame is displayed in black, second in red
            time.sleep(1)  # wait a second for no reason


        if event == '-ORIENT-':
            orient = values['-ORIENT-']    #  get the desired display orientation
            if orient == 'portrait':
                epd.set_rotate(0)          # 0=0deg, 1=90, 2=180 , 3=270deg
            if orient == 'landscape':
                epd.set_rotate(3)
            needToProcessPreviewAgain = True    # this works to populate output lines  since Preview is above here


        if event == 'ReBootRPi':
            os.system("sudo reboot")


        if event == 'UnplugRPi':
            os.system("sudo shutdown -h now")


        if event == 'Debug':
            print(event, values)

        if event == sg.TIMEOUT_KEY:     # gets here each loop that it timed out due to no event from the web
            pass

    window.close()    # due to pressing 'Quit' button or ...

if __name__ == '__main__':
    main()
    print('Program terminating normally')
    os._exit(1)