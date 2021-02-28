#!/usr/bin/python3
# coding: utf-8
from os import path, getcwd, environ 
import locale
import secrets
import webbrowser
import gettext
import sys
import re
import AESifyIcons as icons
import PySimpleGUI as sg
import pyperclip
from pikepdf import Pdf, Page, Permissions, Encryption, PasswordError, PdfError, _cpphelpers 

# Needed for pyinstaller onefile...
try:
    workingDirectory = sys._MEIPASS
except Exception:
    workingDirectory = getcwd()
    
#snap debug info
if "SNAP_COMMON" in environ:
    message = 'locale.getdefaultlocale()[0] =' + locale.getdefaultlocale()[0] + ' - '
    message = message + 'CWD' + getcwd() + ' - '
    message = message + 'Environment' + str(environ)
    popWindow = sg.Window('',
        [[sg.Multiline(message)]
        ],         
        auto_size_text = True,
        finalize = True  
    )
    
# Environment of Windows executable created with cxFreeze seems to have no language setting in environ
if "LANG" not in environ:
    environ['LANG'] = locale.getdefaultlocale()[0] 

# Set up translation, fall back to default if no translation file is found 
localization = gettext.translation('AESify', localedir=workingDirectory + '/locale', fallback=True)
localization.install()
_=localization.gettext

aboutPage = 'https://github.com/digidigital/AESify/blob/main/About.md'
version = '1.5.1'
applicationTitle = _('AESify {0} - Encrypt PDF-Files Easily').format(version)
showPasswordText = _('Show password')
copyPasswordText = _('Copy password to clipboard')
openPasswordText = _('Password used to open the document - Limited to non-restricted actions')
permissionsPasswordText = _('If the document is opened with this password the user is not limited by document restrictions')
createPasswordText=_('Create password')
copyString=_('Copy') + '::Copy'
pasteString=_('Paste') + '::Paste'

# Characters that can be misinterpreted by humans (1 I l | O 0 o ' ` , . / \ ;) and some hard to reach special characters have been removed 
passwordPool = '23456789abcdefghjkmnrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ!#$%&()*+-<=>?@[]_:' 

theme='DefaultNoMoreNagging'
sg.theme(theme)   
background = sg.LOOK_AND_FEEL_TABLE[theme]['BACKGROUND']

# Toggles between visible and masked view by switching between two text fields. Workaround since I did not find a method in pySimpleGUI to update password_char :(
def togglePassword(button, maskedText, clearText):
    if event == button and  window[maskedText].Visible:
        window[maskedText].update(visible=False)
        window[maskedText].Visible = False
        window[clearText].update(visible=True)
    else:
        window[maskedText].update(visible=True)
        window[maskedText].Visible = True
        window[clearText].update(visible=False)

# Syncs the password value between masked and visible text fields
def syncPasswords(maskedText, clearText):
    if event == maskedText:
        window[clearText].update(value=values[maskedText])
        synchedPassword = values[maskedText]
    elif event == clearText:
        window[maskedText].update(value=values[clearText])
        synchedPassword = values[clearText]
    return synchedPassword    

# If filename is longer than 'limit' split filename in two shorter parts an add '...' in the middle so it fits in limit
def limitFilenameLen(filename, limit=67):
    x = len(filename)
    if x <= limit:
        return filename
    else:
        return filename[0:int(limit/2 - 3)] + '...' + filename[x - int(limit/2 - 3):x]       

# Evaluate the complexity of the password and return a score
def evalPassword(password):
    passwordScore = 0   

    # Password needs at least 8 letter to get a score
    if len(password) >= 8: 
        # Password does contain no sequence of more than two consecutive letters of the same type
        if not re.search(r'[A-ZÄÖÜ]{3}|[a-zäöü][a-zäöü][a-zäöü]|[\d][\d][\d]|[\W][\W][\W]', password) or len(password) >= 16: 
            passwordScore += 3
           
        # Password contains at least one uppercase letter
        if re.search(r'[A-ZÄÖÜ]', password):
            passwordScore += 1
            
        # Password contains at least one lowercase letter
        if re.search(r'[a-zäöü]', password):
            passwordScore += 1  
            
        # Password contains at least one special character
        if re.search(r'[\W]', password):# Add Check for invalid Characters later !!! and not re.search(r'[\s"]' , values['-Password-']):
            passwordScore += 1    
            
        # Password contains at least one digit
        if re.search(r'\d', password):
            passwordScore += 1 
            
        # Additional score for length
        if len(password) >= 10:    
            passwordScore += 2    

    return passwordScore       

# Just a simple popup message in a function so I can change formatting and behaviour in one place. :)
def popUp(message):
    windowLocation = window.current_location()
    popWindow = sg.Window('',
        [[sg.Text(message)],
        [sg.OK()]
        ], 
        element_justification = 'c',
        no_titlebar = True,
        font=('Helvetica'),
        auto_close= True,
        auto_close_duration = 10,
        modal=True,
        finalize = True, 
        keep_on_top = True,
        location = (windowLocation[0]+window.size[0]/3,windowLocation[1]+window.size[1]/3)
        
    )
        
    while True:
        event, values = popWindow.read() 
        if event == sg.WIN_CLOSED: 
            break
        else:
            popWindow.close()
            
# Updates the permission checkboxes according to pdf´s attributes
def updatePermission(pdf, permission, checkboxName):
    if getattr(pdf.allow, permission):
        window[checkboxName].update(value = True)
    else:    
        window[checkboxName].update(value = False) 

def updatePassword(key, password):
    key = re.sub('Create', '', key)
    key = re.sub('-', '', key)
    window['-' + key + '-'].update(value = password)
    window['-' + key + 'Masked-'].update(value = password) 
    key = re.sub('Password', '', key)
    window['-Complexity' + key + '-'].update_bar(evalPassword(password))

# Check if pyperclip dependencies are installed
if sys.platform.startswith('linux'):   
    if pyperclip._executable_exists('xclip') or pyperclip._executable_exists('xsel') or pyperclip._executable_exists('wl-clipboard'):
        copyPasteEnabled=True
        rightClickMenu=[copyString, pasteString]
    else:
        sg.popup_no_titlebar(_("In order to use right click copy/paste please install package 'xclip', 'xsel or 'wl-clipboard'. You can still use 'CTRL + v' to paste passwords."))
        copyPasteEnabled=False
        rightClickMenu=[]
else:
    copyPasteEnabled=True
    rightClickMenu=[copyString, pasteString]

# Centralized layout settings
textSizeDefault=(58,1)
sliderSizeDefault=(50,20)
progressBarSizeDefault=(48,20)

# Define columns
column1 = [
    [sg.Text(_('Input Settings'), font=('Helvetica', 15), justification='left')], 
    [sg.Text(_('PDF:'), size=(21,1)), 
        sg.InputText(k='-FilenameShort-', size=textSizeDefault, readonly=True), 
        sg.InputText(k='-Filename-', visible=False,  readonly=True, enable_events=True), 
        sg.FileBrowse(_('Browse'), file_types=(("PDF", "*.pdf"),),)
    ],
    [sg.Text(_('Password:'), size=(21,1)), 
        sg.Column([[
            sg.InputText(k='-PasswordInMasked-', 
            size=textSizeDefault, password_char='*', 
            enable_events=True, 
            right_click_menu = ( ['-PasswordInMenu-', rightClickMenu])), 
            sg.InputText(k='-PasswordIn-', size=textSizeDefault, visible=False,  enable_events=True)
        ]], k='-PasswordInColumn-',pad=(0,0)), 
        sg.Button(image_data=icons.eyeIcon_base64, k='-ShowPasswordIn-', enable_events=True, tooltip=showPasswordText, border_width=0, button_color=('black',background)), 
        sg.Button(image_data=icons.docIcon_base64, k='-CopyPasswordIn-', enable_events=True, tooltip=copyPasswordText, visible=copyPasteEnabled, border_width=0, button_color=('black',background))
    ]
]

column2 = [
    [sg.Text(_('About'), k='-About-',justification='right', enable_events=True)],
    [sg.Image(data=icons.shieldIconLarge_base64, k='-Shield-', size=(90,90), enable_events=True)], 
                                 
]

column3 = [
    [sg.Text(_('Output Settings'), font=('Helvetica', 15), justification='left')], 
    [sg.Text(_('Encrypted PDF:'), size=(21,1)), sg.InputText(k='-FilenameOutShort-', size=textSizeDefault , readonly=True), 
        sg.InputText(k='-FilenameOut-', visible=False, readonly=True, enable_events=True), 
        sg.SaveAs(_('Browse'), file_types=(("PDF", "*.pdf"),),)
    ],
    [sg.Text(_('Open Password:'), tooltip=openPasswordText, size=(21,1)), 
        sg.Column([
            [sg.InputText(k='-PasswordUserMasked-', size=textSizeDefault, tooltip=openPasswordText, change_submits=True, password_char='*', enable_events=True, right_click_menu = (['-PasswordUserMenu-', rightClickMenu])), 
                sg.InputText(k='-PasswordUser-', size=textSizeDefault, change_submits=True, visible=False, enable_events=True)
            ]
        ], k='-PasswordUserColumn-', pad=(0,0)), 
        sg.Button(image_data=icons.eyeIcon_base64, k='-ShowPasswordUser-', tooltip=showPasswordText, enable_events=True, border_width=0, button_color=('black',background)), 
        sg.Button(image_data=icons.diceIcon_base64, k='-PasswordUserCreate-', tooltip=createPasswordText, enable_events=True, border_width=0, button_color=('black',background)), 
        sg.Button(image_data=icons.docIcon_base64, k='-CopyPasswordUser-', tooltip=copyPasswordText, visible=copyPasteEnabled, enable_events=True, border_width=0, button_color=('black',background))],
    [sg.Text(_('Complexity:'), size=(21,1)), 
        sg.ProgressBar(9, orientation='h', size=progressBarSizeDefault, key='-ComplexityUser-')
    ],
    [sg.Text(_('Permissions Password:'), tooltip=permissionsPasswordText, size=(21,1)), 
        sg.Column([
            [sg.InputText(k='-PasswordOwnerMasked-', size=textSizeDefault, change_submits=True, tooltip=permissionsPasswordText, password_char='*', enable_events=True, right_click_menu = (['-PasswordOwnerMenu-', rightClickMenu])), 
                sg.InputText(k='-PasswordOwner-', size=textSizeDefault, change_submits=True, visible=False, enable_events=True)
            ]
        ], k='-PasswordOwnerColumn-', pad=(0,0)), 
        sg.Button(image_data=icons.eyeIcon_base64, k='-ShowPasswordOwner-', tooltip=showPasswordText, enable_events=True, border_width=0, button_color=('black',background)), 
        sg.Button(image_data=icons.diceIcon_base64, k='-PasswordOwnerCreate-', tooltip=createPasswordText, enable_events=True, border_width=0, button_color=('black',background)),
        sg.Button(image_data=icons.docIcon_base64, k='-CopyPasswordOwner-', tooltip=copyPasswordText, visible=copyPasteEnabled, enable_events=True, border_width=0, button_color=('black',background))
    ],
    [sg.Text(_('Complexity:'), size=(21,1)), 
        sg.ProgressBar(9, orientation='h', size=progressBarSizeDefault, key='-ComplexityOwner-')
    ], 
    [sg.Text(_('Encryption level:'), size=(21,1)), 
        sg.Radio('128-Bit AES', "RADIO1", k='AES128Bit', size=(20,1)), 
        sg.Radio('256-Bit AES', "RADIO1", k='AES256Bit', default=True)
    ],
    [sg.Text(_('Page range from:'), size=(21,1)), 
        sg.InputText(k='-PageFrom-', default_text='1', readonly=True, size=(4,1), enable_events=True), 
        sg.Slider(k='-PageFromSlider-', resolution=1, disable_number_display=True, size=sliderSizeDefault, range=(1,99), orientation='h', enable_events=True)
    ],
    [sg.Text(_('Page range to:'), size=(21,1)), 
        sg.InputText(k='-PageTo-', default_text='1', readonly=True, size=(4,1), enable_events=True), 
        sg.Slider(k='-PageToSlider-', resolution=1, disable_number_display=True, size=sliderSizeDefault, range=(1,99), orientation='h', enable_events=True)
    ],
    [sg.Button(_('Save PDF'), k='Save PDF', pad=((5,0),(15,10)))]
]

column4 = [
    [sg.Frame(layout=[      
        [sg.Checkbox(_('High Resolution printing'), k='print_highres', tooltip=_('Allow high quality prints'), enable_events=True, default=True)],
        [sg.Checkbox(_('Low Resolution Printing (150dpi)'), k='print_lowres', tooltip=_('Allow a print quality of 150dpi'), enable_events=True, default=True)],
        [sg.Checkbox(_('Document Assembly'), k='modify_assembly', tooltip=_('Allow adding/inserting and rotating of pages'), default=True)],
        [sg.Checkbox(_('Content Copying'), k='extract', tooltip=_('Allow copying of text, images, etc.'), default=True)], 
        [sg.Checkbox(_('Commenting'), k='modify_annotation', tooltip=_('Allow commenting, form field fill-in and signing'), default=True)],
        [sg.Checkbox(_('Form field fill-in or signing'), k='modify_form', tooltip=_('Allow form field fill-in, signing and creation of template pages'), default=True)],
        [sg.Checkbox(_('Forms, Signing, Template Pages'), k='modify_other', tooltip=_('Allow changing the document, document assembly, form field fill-in, signing and creation of template pages'), default=True)]      
    ], title=_('Document Restrictions'), relief=sg.RELIEF_SUNKEN)]
]

layout = [ 
        [sg.Column(column1),sg.Column(column2, expand_x=True, element_justification='c'),], 
        [sg.HorizontalSeparator(color='black', pad=(0,15))],
        [sg.Column(column3), sg.Column(column4)],                                  
]

# Create the Window
window = sg.Window(applicationTitle, layout, font=('Helvetica'), icon=icons.shieldIcon_base64, finalize=True) 
# Bind mouseover to password columns so we know where to copy/paste in the event loop
window['-PasswordInColumn-'].bind('<Enter>', '_MOUSEOVER')
window['-PasswordUserColumn-'].bind('<Enter>', '_MOUSEOVER')
window['-PasswordOwnerColumn-'].bind('<Enter>', '_MOUSEOVER')

# Event Loop to process "events" and get the "values" of the inputs
while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED: 
        break
    
    # Manage "Show password" feature
    togglePassword('-ShowPasswordIn-','-PasswordInMasked-','-PasswordIn-')
    togglePassword('-ShowPasswordUser-','-PasswordUserMasked-','-PasswordUser-')
    togglePassword('-ShowPasswordOwner-','-PasswordOwnerMasked-','-PasswordOwner-')

     # Remember column mouseover event to be able to identify the text field where we need to copy/paste   
    if event == '-PasswordInColumn-_MOUSEOVER':
        activePasswordField='-PasswordIn-'
    
    if event == '-PasswordUserColumn-_MOUSEOVER':
        activePasswordField='-PasswordUser-'
        
    if event == '-PasswordOwnerColumn-_MOUSEOVER':
        activePasswordField='-PasswordOwner-'

    # Copy password via right click menu or icon button
    if event == '-CopyPasswordIn-' or ('::Copy' in event and activePasswordField == '-PasswordIn-'):
        pyperclip.copy(values['-PasswordIn-'])
        
    if event == '-CopyPasswordUser-' or ('::Copy' in event and activePasswordField == '-PasswordUser-'):
        pyperclip.copy(values['-PasswordUser-'])
        
    if event == '-CopyPasswordOwner-' or ('::Copy' in event and activePasswordField == '-PasswordOwner-'):
        pyperclip.copy(values['-PasswordOwner-'])
        
    # Manage pasting passwords
    # In case of passwords for the encrypted PDF evaluate passsword strength
    # and update complexity bar
    if '::Paste' in event  and activePasswordField == '-PasswordIn-': 
        window['-PasswordIn-'].update(value=pyperclip.paste())
        window['-PasswordInMasked-'].update(value=pyperclip.paste())
           
    if '::Paste' in event and activePasswordField == '-PasswordUser-': 
        newpassword=str(pyperclip.paste())
        window['-PasswordUser-'].update(value=newpassword)
        window['-PasswordUserMasked-'].update(value=newpassword)
        window['-ComplexityUser-'].update_bar(evalPassword(newpassword))

    #s contains ::Paste
    if '::Paste' in event and activePasswordField=='-PasswordOwner-': 
        newpassword=str(pyperclip.paste())
        window['-PasswordOwner-'].update(value=newpassword)
        window['-PasswordOwnerMasked-'].update(value=newpassword)
        window['-ComplexityOwner-'].update_bar(evalPassword(newpassword))

    # Synch visible and invisible password fields if password is changed
    # In case of passwords for the encrypted PDF evaluate passsword strength
    # and update complexity bar
    if event == '-PasswordInMasked-' or event == '-PasswordIn-':
        syncPasswords('-PasswordInMasked-','-PasswordIn-')  

    if event == '-PasswordUserMasked-' or event == '-PasswordUser-':
        window['-ComplexityUser-'].update_bar(evalPassword(syncPasswords('-PasswordUserMasked-','-PasswordUser-'))) 

    if event == '-PasswordOwnerMasked-' or event == '-PasswordOwner-':
        window['-ComplexityOwner-'].update_bar(evalPassword(syncPasswords('-PasswordOwnerMasked-','-PasswordOwner-')))  
   
    # Switch off highres printing permission checkbox if lowres printing is selected
    if event == 'print_lowres':
        if (values['print_lowres'] and values['print_highres']) or (not values['print_lowres'] and values['print_highres']) :        
            window['print_highres'].update(value = False)   

    # Switch on lowres printing permission checkbox if highres printing is selected
    if event == 'print_highres' and not values['print_lowres'] and values['print_highres']:        
        window['print_lowres'].update(value = True)

    if event == '-Filename-' and not values['-Filename-'] == '' : 
        # Shorten filename so it fits in the input text field
        window['-FilenameShort-'].update(value = limitFilenameLen(values['-Filename-']))
              
        # Try to open PDF and read page count, set sliders to min and max pagecount
        try:     
            pdf = Pdf.open(values['-Filename-'], password=str(values['-PasswordIn-']))
           
           # Update pagerange sliders to new min and max values after new PDF was selected 
            window['-PageFromSlider-'].update(range = (1,len(pdf.pages)), value = 1 )
            window['-PageFrom-'].update(value = 1)
            window['-PageToSlider-'].update(range = (1,len(pdf.pages)))
            window['-PageTo-'].update(value = len(pdf.pages))
            window['-PageToSlider-'].update(value = len(pdf.pages)) 

            # Update document restriction/ permission checkboxes          
            updatePermission(pdf, 'extract', 'extract')
            updatePermission(pdf, 'modify_annotation', 'modify_annotation')
            updatePermission(pdf, 'modify_assembly', 'modify_assembly')
            updatePermission(pdf, 'modify_form', 'modify_form')
            updatePermission(pdf, 'modify_other', 'modify_other')
            updatePermission(pdf, 'print_highres', 'print_highres')
            if pdf.allow.print_highres:
                window['print_lowres'].update(value = False)
            else:                
                updatePermission(pdf, 'print_lowres', 'print_lowres')
                       
            pdf.close()
            
            #If no filename for outfile is set set a standard one
            if values['-FilenameOut-'] == '':
                inPath, inFilename = path.split(values['-Filename-'])
                outfile = inPath + "/encrypted-" + inFilename 
                window['-FilenameOut-'].update(value = outfile)
                window['-FilenameOutShort-'].update(value = limitFilenameLen(outfile))
        
        except PasswordError:
            popUp(_('Missing or wrong password'))
            window['-Filename-'].update(value = '')
            window['-FilenameShort-'].update(value = '')

        except PdfError:
            popUp(_('Unable to open file.'))
            window['-Filename-'].update(value = '')
            window['-FilenameShort-'].update(value = '')

    # Check length of manually selected filename and shorten it to fit in text field if necessary
    if event == '-FilenameOut-' and not values['-FilenameOut-'] == '': 
        window['-FilenameOutShort-'].update(value = limitFilenameLen(values['-FilenameOut-']))

    # Synch "pagerange from" slider with displayed text
    if event == '-PageFromSlider-': 
        window['-PageFrom-'].update(value = int(values['-PageFromSlider-']))
        if values['-PageFromSlider-'] > values['-PageToSlider-']:
            window['-PageTo-'].update(value = int(values['-PageFromSlider-']))
            window['-PageToSlider-'].update(value = int(values['-PageFromSlider-']))
    
    # Synch "pagerange to" slider with displayed text
    if event == '-PageToSlider-': 
        window['-PageTo-'].update(value = int(values['-PageToSlider-']))
        if values['-PageToSlider-'] < values['-PageFromSlider-']:
            window['-PageFrom-'].update(value = int(values['-PageToSlider-']))
            window['-PageFromSlider-'].update(value = int(values['-PageToSlider-']))
    
    # Open about page in Webbrowser
    if event == '-About-' or event == '-Shield-':
        webbrowser.open(aboutPage)    

    if event == '-PasswordOwnerCreate-' or event == '-PasswordUserCreate-':
        while True:
            randomPassword = ''.join(secrets.choice(passwordPool) for i in range(32))
            if (sum(c.islower() for c in randomPassword) >= 3
                    and sum(c.isupper() for c in randomPassword) >= 3
                    and sum(c.isdigit() for c in randomPassword) >= 3):
                break
        updatePassword(event, randomPassword)

    # Encrypt and save PDF
    if event == 'Save PDF':                     
        if values['-Filename-'] != '':
            
            # Some validity checks
            if values['-PasswordOwner-'] == '' and values['-PasswordUser-'] != '':
                popUp(_('Error: If the owner password is blank the open passwort should be blank as well.'))
                 
            elif re.search(r'[\s"]', values['-PasswordUser-']):
                popUp(_('The open password contains invalid characters.'))
                  
            elif re.search(r'[\s"]', values['-PasswordOwner-']):
                popUp(_('The owner password contains invalid characters.'))
                                     
            else:
                #Try to encrypt and save the document
                try:      
                    pdf = Pdf.open(values['-Filename-'], password=str(values['-PasswordIn-']))
                
                    # Delete pages from source PDF file (only in memory) to adjust to selected page range
                    if int(values['-PageTo-']) < len(pdf.pages):
                        del pdf.pages[int(values['-PageTo-']):len(pdf.pages)]
                    if int(values['-PageFrom-']) > 1:
                        del pdf.pages[0:(int(values['-PageFrom-'])-1)]  
                
                    # Create Permission Object
                    outPermissions = Permissions( 
                            extract=values['extract'], 
                            modify_annotation=values['modify_annotation'], 
                            modify_assembly=values['modify_assembly'], 
                            modify_form=values['modify_form'], 
                            modify_other=values['modify_other'], 
                            print_lowres=values['print_lowres'], 
                            print_highres=values['print_highres']
                    )
                                      
                    # Save file      
                    pdf.save(values['-FilenameOut-'], encryption=Encryption(user=values['-PasswordUser-'], owner=values['-PasswordOwner-'], allow=outPermissions))
                    
                    pdf.close()
                    
                    popUp(_('File saved.'))
                except:
                    popUp(_('An unexpected error occured... :('))
        else:    
            popUp(_('Please select an input file first!'))
            
window.close()
