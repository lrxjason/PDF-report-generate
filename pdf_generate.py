## PDF
import reportlab
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib import colors

from tqdm import tqdm
import pandas as pd
import math
import cv2
import os
import re



### Function for target address center lat long computation ###
def image_info_to_center_lat_lon(image_info, zoom, flag = 1):
    '''
    image_info is '[topleft tile x,
                    topleft tile y,
                    bottom right tile x,
                    bottom right tile y]'
    flag = 0 : NW-corner of the square
    flag = 1 : center
    flag = 2 : Other corner
    '''
    image_info_array = image_info.split(',')
    if flag == 0:
        xtile = (int(image_info_array[0][1:]) + int(image_info_array[2]))//2
        ytile = (int(image_info_array[1]) + int(image_info_array[3][:-1]))//2
    
    elif flag == 1:
        xtile = (int(image_info_array[0][1:]) + int(image_info_array[2]) + 1)//2
        ytile = (int(image_info_array[1]) + int(image_info_array[3][:-1]) + 1)//2

    elif flag ==2:
        xtile = (int(image_info_array[0][1:]) + int(image_info_array[2]) + 2)//2
        ytile = (int(image_info_array[1]) + int(image_info_array[3][:-1]) + 2)//2
    else:
        print('flag is not defined. Using NW-corner of the square')
        xtile = (int(image_info_array[0][1:]) + int(image_info_array[2]))//2
        ytile = (int(image_info_array[1]) + int(image_info_array[3][:-1]))//2

    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return [lat_deg, lon_deg]



dstFolder = 'address'
srcFolder = 'address'
all_address_csv = pd.read_csv(os.path.join(dstFolder, 'all_address.csv'))
cfg ={}
cfg['version'] = '2.2.2'

key_name = all_address_csv.columns
key_name_index = all_address_csv.columns.get_loc('Total points')
pixels_area_key = all_address_csv.columns.get_loc('Roof area pixels')
skylight_key = all_address_csv.columns.get_loc('Skylight')

for address_index, row in tqdm(all_address_csv.iterrows(), total=all_address_csv.shape[0]):
    address = row["Output address"]
    print(f'index:{address_index}, address:{address}')
    if row["Total points"] != row["Total points"] or row["Overall roof condition score"] != row["Overall roof condition score"] : # it is nan
        continue
    # initializing variables with values
    url_zoom_level = row["Image level"]
    cat_lon_coord = image_info_to_center_lat_lon(row["Image info"], url_zoom_level)
    url_lat = cat_lon_coord[0]
    url_lon = cat_lon_coord[1]
    url_date = row['Image date'].replace('-','')

    if row["Image source"] == 'GIC':
        url = f'https://app.gic.org/#/app/home?latitude={url_lat}&longitude={url_lon}&zoom={url_zoom_level}'
    else:
        ### Nearmap url
        url = f'https://apps.nearmap.com/maps/#/@{url_lat},{url_lon},{url_zoom_level}z,0d/V/{url_date}'

    fileName = os.path.join(dstFolder,address+'.pdf')
    documentTitle = f'Refferal'
    # input_address = row['STREET_NAME'] + ',' + row['CITY']+ ',' + row['STATE']+ ',' + str(row['_5_DIGIT_ZIP'])
    input_address = row['location_Address'].replace('/','-')
    title = f'{input_address}'
    subTitle = address

    Damage_image_name = os.path.join(srcFolder,address+'/Damage_merged.jpg')
    Equipment_image_name = os.path.join(srcFolder,address+'/Equipment_merged.jpg')
    # Equipment_image_name = os.path.join(demoFolder,address+'/Roof_condition_merged.jpg')
    # Roof_condition_image_name = os.path.join(demoFolder,address+'/Roof_condition_three_classes_merged.jpg')
    Roof_condition_image_name = os.path.join(srcFolder,address+'/Roof_condition_four_classes_merged.jpg')

    pdf = canvas.Canvas(fileName)
    pdf.setTitle(documentTitle)
    pdf.setFont("Times-Roman", 14)
    pdf.drawCentredString(300, 800, title)

    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Times-Roman", 12)
    pdf.drawCentredString(290, 770, subTitle)

    # drawing a line and version number
    pdf.line(30, 760, 550, 760)
    text = pdf.beginText(520, 10)
    text.setFont("Times-Roman", 8)
    version_information = 'Version: '+ cfg['version']
    text.textLine(version_information)
    pdf.drawText(text)

    # information
    text = pdf.beginText(40, 740)
    text.setFont("Courier", 12)
    text.setFillColor(colors.black)
    image_date = row['Image date']
    text.textLine(f'Image date: {image_date}')

    # line = f'Roof conditon score: {roof_condition_score[address_index]}'
    line = 'Roof condition (roof number/score/confidence) : '
    roof_condition_socres = re.findall(r'\:(.*?)\,', row["Condition details"])
    roof_confidence_socres = re.findall(r'\:(.*?)\,', row["Confidence details"])
    for i in range(len(roof_condition_socres)):
        if i%6==0:
            text.textLine(line)
            line = ''
        line+= f'#{i+1}/{int(float(roof_condition_socres[i]))}/{int(float(roof_confidence_socres[i]))}%  '

    text.textLine(line)
    total_point = 0
    text.setFillColor(colors.blue)

    SB_score = row["Small business unit score"]
    total_confidence = row["Overall roof confidence score"]
    line= f'Small business unit score/condfidence: {int(SB_score)}/{int(total_confidence)}%'
    text.textLine(line)
    text.setFillColor(colors.blue)
    #################################
    for i in range(key_name_index+1, len(key_name)):
        if i == pixels_area_key:
            gsd_area = row["Image gsd (sqft/pixel)"] * row["Roof area pixels"]
            text.textLine(f'Footprint area: {int(gsd_area)} ft\u00b2')
            continue
        # the key_name is from total point to end. So using key to find skylight
        if i == skylight_key:
            if 0 < row["Number of Skylight"] < 5:
                line = key_name[i] + ': ' + f'A few ({int(row["Number of Skylight"])})'
                text.textLine(line)
                continue
            if row["Number of Skylight"] >=5:
                line = key_name[i] + ': ' + f'Many ({int(row["Number of Skylight"])})'
                text.textLine(line)
                continue 

        if int(row[i]) == 0:
            line = key_name[i] + ': ' + 'Not detected'
            # text.textLine(line)     # Hide no detected case
        elif int(row[i]) == 1:
            if key_name[i] == 'Pipeline' or key_name[i] =='Solar panel': 
                line = key_name[i] + ': ' + 'Detected'
                text.textLine(line)
            if key_name[i] == 'Staining' or key_name[i] =='Water pooling' or key_name[i] =='Other damage' or key_name[i] =='Patching':
                line = key_name[i] + ': ' + 'Minor'
                text.setFillColor(colors.magenta)
                text.textLine(line)
                text.setFillColor(colors.blue)
            if key_name[i] =='HVAC/Cooling tower':
                # line = key_name[i] + ': ' + 'Minimal'
                line = key_name[i] + ': ' + f'Minimal ({int(row["Number of HVAC/Cooling tower"])})'
                text.textLine(line)
        elif int(row[i]) == 2:
            if key_name[i] == 'Pipeline' or key_name[i] =='Solar panel': 
                line = key_name[i] + ': ' + 'Detected'
                text.textLine(line)
            if key_name[i] == 'Staining' or key_name[i] =='Water pooling' or key_name[i] =='Other damage' or key_name[i] =='Patching':
                line = key_name[i] + ': ' + 'Moderate'
                text.setFillColor(colors.magenta)
                text.textLine(line)
                text.setFillColor(colors.blue)
            if key_name[i] =='HVAC/Cooling tower':
                # line = key_name[i] + ': ' + 'A few'
                line = key_name[i] + ': ' + f'A few ({int(row["Number of HVAC/Cooling tower"])})'
                text.textLine(line)
        else:
            if key_name[i] == 'Pipeline' or key_name[i] =='Solar panel' or key_name[i] =='Tarp': 
                line = key_name[i] + ': ' + 'Detected'
                text.textLine(line)
            if key_name[i] == 'Staining' or key_name[i] =='Water pooling' or key_name[i] =='Other damage' or key_name[i] =='Patching':
                line = key_name[i] + ': ' + 'Major'
                text.setFillColor(colors.magenta)
                text.textLine(line)
                text.setFillColor(colors.blue)
            if key_name[i] =='HVAC/Cooling tower':
                # line = key_name[i] + ': ' + 'Many'
                line = key_name[i] + ': ' + f'Many ({int(row["Number of HVAC/Cooling tower"])})'
                text.textLine(line)

    pdf.drawText(text)

    textLines = ['Condition',
                'Damage',
                'Equipment'
    ]
    image_name = address + '.jpg'
    image_full_name = os.path.join(srcFolder,image_name)

    image = cv2.imread(image_full_name)
    height = image.shape[0]
    width = image.shape[1]
    ratio = width/height

    if height < width: # height < width horizontal
        tmp_width = 350
        tmp_height = 180
        new_width = ratio * tmp_height
        if new_width > tmp_width:
            draw_width = tmp_width
            draw_height = draw_width/ratio
        else:
            draw_width = new_width
            draw_height = tmp_height
        text = pdf.beginText(100, 500)
        text.setFont("Courier", 12)
        text.setFillColor(colors.blue)
        text.textLine(textLines[-3])
        pdf.drawText(text)
        # pdf.drawInlineImage(image_full_name, 230, 440, width = draw_width, height = draw_height)
        pdf.drawInlineImage(Roof_condition_image_name, 230, 440, width = draw_width, height = draw_height)
        pdf.linkURL(url, (200, 440, 230+draw_width, 440+draw_height), relative=1)
# https://apps.nearmap.com/maps/#/@30.6622190,-88.1816001,20.00z,0d/V/20220110

        text = pdf.beginText(100, 300)
        text.setFont("Courier", 12)
        text.setFillColor(colors.blue)
        text.textLine(textLines[-2])
        pdf.drawText(text)
        pdf.drawInlineImage(Damage_image_name, 230, 240, width = draw_width, height = draw_height)
        pdf.linkURL(url, (200, 240, 230+draw_width, 240+draw_height), relative=1)


        text = pdf.beginText(100, 100)
        text.setFont("Courier", 12)
        text.setFillColor(colors.blue)
        text.textLine(textLines[-1])
        pdf.drawText(text)
        pdf.drawInlineImage(Equipment_image_name, 230, 40, width = draw_width, height = draw_height)
        pdf.linkURL(url, (200, 40, 230+draw_width, 40+draw_height), relative=1)

    else: # vertical
        tmp_width = 250
        tmp_height = 300
        new_width = ratio * tmp_height
        if new_width > tmp_width:
            draw_width = tmp_width
            draw_height = draw_width/ratio
        else:
            draw_width = new_width
            draw_height = tmp_height
        text = pdf.beginText(310, 370)
        text.setFont("Courier", 12)
        text.setFillColor(colors.blue)
        text.textLine(textLines[-3])
        pdf.drawText(text)
        # pdf.drawInlineImage(image_full_name, 310, 380, width = draw_width, height = draw_height)
        pdf.drawInlineImage(Roof_condition_image_name, 310, 380, width = draw_width, height = draw_height)
        pdf.linkURL(url, (310, 380, 310+draw_width, 380+draw_height), relative=1)

        text = pdf.beginText(40, 30)
        text.setFont("Courier", 12)
        text.setFillColor(colors.blue)
        text.textLine(textLines[-2])
        pdf.drawText(text)
        pdf.drawInlineImage(Damage_image_name, 40, 40, width = draw_width, height = draw_height)
        pdf.linkURL(url, (40, 40, 40+draw_width, 40+draw_height), relative=1)


        text = pdf.beginText(310, 30)
        text.setFont("Courier", 12)
        text.setFillColor(colors.blue)
        text.textLine(textLines[-1])
        pdf.drawText(text)
        pdf.drawInlineImage(Equipment_image_name, 310, 40, width = draw_width, height = draw_height)
        pdf.linkURL(url, (310, 40, 310+draw_width, 40+draw_height), relative=1)

    # saving the pdf
    pdf.save()



