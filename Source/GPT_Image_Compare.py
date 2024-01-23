# Project: GPT_Compare_Images - test GPT's ability to compare images
# Author - Stephen Witty switty@level500.com
# Started 1-19-24
# Description - ask GPT to compare two images and ask if object in the photograph is the same object
# Example used from openai for vision gpt
# To run:
#     tested on ubuntu
#     install OpenAI Python lib (see OpenAI website for instructions)
#     install ImageMagic to gain access to the "convert" command
#     install package with banner command
#
# V1 1-19-24   Initial development
# V2 1-22-24   Fixed typo in prompt

import random
import time
import os
import sys
import base64
import requests
import subprocess
import re

# OpenAI API Key
api_key = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

##################### Constants ###########################################################################################
COUNT = 10                                              # Number of times to run the test
PIC_DIR = "/home/switty/dev/GPT_Image_Compare/pics"     # Picture directory  location fully pathed, do not include / on end
DELAY = 4                                               # Delay time per test run to display results in seconds
###########################################################################################################################

# Function to encode the image
def encode_image(image_path):
   with open(image_path, "rb") as image_file:
      return base64.b64encode(image_file.read()).decode('utf-8')

print("GPT Image Compare Starting....")
print("Image directory: " + str (PIC_DIR))

# Delete all temp file that is used to combine two photos for submission
os.system("rm -f " + PIC_DIR + "/pic.jpg")

try:
   filenames_with_path = []  # Store picture names with full path
   filenames_no_path = []    # Store picture names with only the file name
   for entry in os.listdir(PIC_DIR):
      full_path = os.path.join(PIC_DIR,entry)
      if (os.path.isfile(full_path) and (entry.endswith('.JPG') or entry.endswith('.jpg'))):
         filenames_with_path.append(full_path)
         filenames_no_path.append(entry)

except Exception as e:
      print("Error occurred reading pictures: " + str(e))
      print("Exiting")
      os.sys.exit(1)

if (len(filenames_no_path) == 0):
   print("Error no pictures found")
   print("Exiting")
   os.sys.exit(1)

# Put files in order just to make the print out better
filenames_with_path.sort()
filenames_no_path.sort()

print("List of source pictures, total: ",len(filenames_no_path))
print("--------------------------------")
for entry in filenames_with_path:
   print(entry)
print("----------------------------")
for entry in filenames_no_path:
   print(entry)

###################### Main loop #####################################################
total = 0
web_api_error = 0
no_answer = 0
wrong_answer = 0
right_answer = 0
pick_same_object = False  # Using this flag to pick same object at least every other test
bad_first_pics = []       # Using these to store pictures that GPT called wrong
bad_second_pics = []

while (total < COUNT):

   if (total > 0):
      time.sleep(DELAY)
      process.terminate() # This closes the picture display program that is started later

   total = total + 1
   os.system("clear")
   print("Test number: " + str(total) + " ******************************************")

   # Pick photos at random to test
   while(True): # Stay in this loop until pick same object rule is satisfied.  Pick same object at least every other test.
      first_pic = random.randint(0,len(filenames_no_path) - 1)
      second_pic = random.randint(0,len(filenames_no_path) - 1)

      if (filenames_no_path[first_pic].lower()[0] == filenames_no_path[second_pic].lower()[0]):
         same_object = True
      else:
         same_object = False

      if (pick_same_object == False):
         pick_same_object = True
         break;

      if (pick_same_object == True and same_object == True):
         pick_same_object = False
         break;

   print("First pic: " + filenames_no_path[first_pic] + "   Second pic: " + filenames_no_path[second_pic] + "   Same object: " + str(same_object))

   # Put both test images together as one photo to send to GPT
   os.system("rm -f " + PIC_DIR + "/pic.jpg")
   # Append both photos with convert
   os.system("convert " + filenames_with_path[first_pic] + " " + filenames_with_path[second_pic] + " +append " + PIC_DIR + "/pic.jpg")
   # Config image to a smaller resolution , this makes for a better screen display and also saves cost on the GPT call
   os.system("convert " + PIC_DIR + "/pic.jpg -resize 800x600 " + PIC_DIR + "/pic.jpg")
   # Open the image with eog - a Linux image display application
   process = subprocess.Popen(["eog",PIC_DIR+"/pic.jpg"])
   # Delay a little to wait for photo window to open
   time.sleep(.5)
   # Move the display application from the center of the screen to the upper left
   os.system("wmctrl -r " + "\"pic.jpg\" -e 0,0,0,-1,-1")

   # Path to image to feed to GPT, this matches original GPT example setup
   image_path = PIC_DIR + "/pic.jpg"

   # Getting the base64 string
   base64_image = encode_image(image_path)
   headers = {
      "Content-Type": "application/json",
      "Authorization": f"Bearer {api_key}"
   }

   # Construct GPT API json, this is from GPT example code
   payload = {
      "model": "gpt-4-vision-preview",
      "messages": [
         {
            "role": "user",
            "content": [
               {
                  "type": "text",
                  "text": "Are the two objects pictured the same?  Provide back the answer as YES or NO between {}.  For example if the answer is YES then reply back with {YES}.  Provide no other description or details."
               },
               {
                  "type": "image_url",
                  "image_url": {
                     "url": f"data:image/jpeg;base64,{base64_image}"
               }
            }
         ]
      }
   ],
    "max_tokens": 300
   }

   output = {}
   try:
      response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=90)
      output = response.json()
   except Exception as e:
      print("ERROR - Exception on openai web call.")
      print(e)
      web_api_error = web_api_error + 1
      continue

   if (response.status_code != 200  or "error" in output):
      print("ERROR - Received return error from openai web api.  Status code = " + str(response.status_code))
      web_api_error = web_api_error + 1
      if ("error" in output):
         print(output["error"]["message"])
      continue

   if ("choices" not in output):
      print("ERROR - Choices is not in output from GPT")
      web_api_error = web_api_error + 1
      continue

   message = output["choices"][0]["message"]["content"]

#   message = "{no}"  # debug line if needed

################### Extract GPT answer from {} ###################################
# Making several checks to make sure we are getting the answer in the right format
   cnt = 0
   cnt2 = 0
   pos = 0
   for char in message:
      if (char == "{"):
         cnt = cnt + 1
         start = pos
      if (char == "}"):
         cnt2 = cnt2 + 1
         end = pos
      pos = pos + 1

   if (cnt == 0 or cnt2 == 0):
      print("ERROR:  No brackets or incomplete")
      no_answer = no_answer + 1
      continue

   if (cnt > 1 or cnt2 > 1):
      print("ERROR:  Too many brackets in output from GPT")
      no_answer = no_answer + 1
      continue

   if (end < start):
      print("ERROR: Brackets are reversed in output from GPT")
      no_answer = no_answer + 1
      continue

   if ( (end - start) != 3 and (end - start) != 4):
      print("ERROR: Answer is the wrong size (Either 2 or 3 characters)")
      no_answer = no_answer + 1
      continue

   # Parse out the answer in between {}
   answer = ""
   match = re.search(r'\{(.*?)\}',message)
   answer = match.group(1)
   answer = answer.upper()

   # Check and see if the answer is YES or NO
   if (answer != "YES" and answer != "NO"):
      print("ERROR, The answer is not YES or NO")
      no_answer = no_answer + 1
      continue

   print("GPT answer are they the same object: " + answer) 
################ End Extract GPT answer #######

   good = False # This controls the good or bad banner
   if (same_object == True):  # Figure out if GPT got it right or not
      if (answer == "YES"):
         right_answer = right_answer + 1
         good = True
      else:
         wrong_answer = wrong_answer + 1
   else:
      if (answer == "NO"):
         right_answer = right_answer + 1
         good = True
      else:
         wrong_answer = wrong_answer + 1

   print("API errors: " + str(web_api_error) + "   No answer: " + str(no_answer) + "   Wrong answer: " + str(wrong_answer) + "   Right answer: " + str(right_answer) + "\n")

   if (good == False): # Print good or bad banners
      bad_first_pics.append(filenames_no_path[first_pic])   # Store image names that GPT got wrong
      bad_second_pics.append(filenames_no_path[second_pic])
      os.system("banner \"Bad Answer\"")
   else:
      if (same_object == True):
         os.system("banner \"Match\"")
      else:
         os.system("banner \"No Match\"")

############################## End of main test loop ##################3

time.sleep(DELAY)
process.terminate()

# End of tests, print final data
print("**************** End Report ********************")
print("Web API errors: " + str(web_api_error))
print("Bad answer format: " +  str(no_answer))
print("Right answers: " + str(right_answer))
print("Wrong answers: " + str(wrong_answer))
print("************************************************")
if (wrong_answer > 0):
   print("Set of pictures GPT got wrong")
   count = 0
   for entry in bad_first_pics:
      print(entry + " " + bad_second_pics[count])
      count = count + 1

# Clean up temp picture for dual image to GPT
os.system("rm -f " + PIC_DIR + "/pic.jpg")
