import zmq
import time
import os
import requests

import visualGlobals
import postureMain

from SheetVision import main
from midiFogLayer import transposeToBFlat, remove_last_note_events

import cloud

import json

# Function to wait for an external signal from the website and fetch image
def wait_for_website_signal():
    print("Waiting for signal from website...")
    while len(visualGlobals.sheetMusicName) == 0 and len(visualGlobals.imagePath) == 0:
        try:
            response = requests.get("http://192.168.4.45:5000/check")
            if response.status_code == 200:
                data = response.json()
                visualGlobals.sheetMusicName = data.get("title")
                visualGlobals.imagePath = data.get("imagePath")
                print(f"Received title: {visualGlobals.sheetMusicName}, image path: {visualGlobals.imagePath}")

                # Fetch the image
                image_response = requests.get(f"http://192.168.4.45:5000/get_image", params={"imagePath": visualGlobals.imagePath})
                if image_response.status_code == 200:
                    with open(visualGlobals.imagePath, 'wb') as f:
                        f.write(image_response.content)
                    print(f"Image saved to {visualGlobals.imagePath}")
                else:
                    print("Failed to fetch image from server")
            else:
                print("No data yet. Waiting...")
        except Exception as e:
            print(f"Error fetching data: {e}")
        time.sleep(2)  # Poll every 2 seconds
    print("Received signal from website")

# Function to send a file to the client
def send_file_and_string(socket, client_id, filepath, sheetMusicName):
    try:
        with open(filepath, 'rb') as f:
            file_data = f.read()
        print(f"File {filepath} read successfully with length {len(file_data)}")
        socket.send_multipart([client_id, file_data, sheetMusicName.encode('utf-8')])
        print(f"File {filepath} and sheet music name '{sheetMusicName}' sent to Aural Nano")
    except Exception as e:
        print(f"Failed to send file: {e}")


def grade_posture():
    grade, feedback = postureMain.postureGrading()
    visualGlobals.finalPostureGrade = grade
    visualGlobals.postureFeedbackArray = feedback
    visualGlobals.testDoneFlag = True


# Set up ZMQ context and socket
context = zmq.Context()
socket = context.socket(zmq.ROUTER)  # ROUTER socket for more complex communication
socket.bind("tcp://192.168.7.191:5555")  # Bind to port 5555

print("Visual Nano server started, waiting for client...")

while True:
    # Wait for a request from the client
    data = socket.recv_multipart()
    client_id = data[1]
    message = data[2].decode('utf-8')
    print(f"Received request: {message}")

    if message == "NEW_MUSIC":

        visualGlobals.sheetMusicName = ""
        visualGlobals.imagePath = ""
        print("Tell user to enter image and name on website")
        wait_for_website_signal()

        # Run SheetVision to convert visualGlobals.imagePath to MIDI file 
        untransposed_midi_filepath = main.sheetvisionMain(visualGlobals.imagePath)
        transposed_midi_filepath = transposeToBFlat(untransposed_midi_filepath)
        finalized_midi_filepath = remove_last_note_events(transposed_midi_filepath)

        print(f"Transposed MIDI file path: {transposed_midi_filepath}")

        try:
            send_file_and_string(socket, client_id, transposed_midi_filepath, visualGlobals.sheetMusicName)
            os.remove(finalized_midi_filepath)
        except Exception as e:
            print(f"Error with MIDI file: {e}")

    elif message == "TEST":
        visualGlobals.testName = data[3].decode('utf-8')
        print(f"Received test name: {visualGlobals.testName} from Aural Nano. Will perform test and store results in database.")
        
        visualGlobals.testDoneFlag = False
        import threading
        grading_thread = threading.Thread(target=postureMain.postureGrading)
        grading_thread.start()
        
        while not visualGlobals.testDoneFlag:
            try:
                data = socket.recv_multipart(flags=zmq.NOBLOCK)
                message = data[2].decode('utf-8')
                if message == "TEST_DONE":
                    print("Received TEST_DONE signal from Aural Nano.")

                    # Get the finalGrade and Feedback array using globals

                    # Decode the received data from bytes to string and convert to float first
                    musicGrade = float(data[3].decode('utf-8'))

                    # If you need to store the grade as an integer
                    musicGrade = int(musicGrade)

                    feedback_json = data[4].decode('utf-8')  # Decode feedback JSON
                    musicFeedbackArray = json.loads(feedback_json)  # Convert JSON string back to array
                    print(data)

                    finalGrade = None
                    postureFeedbackArray = None 
                    visualGlobals.testDoneFlag = True
                    time.sleep(5)
                    cloud.store_grade_with_files("user1", visualGlobals.testName, visualGlobals.finalPostureGrade, visualGlobals.postureFeedbackArray, musicGrade, musicFeedbackArray )
            except zmq.Again:
                time.sleep(0.1)

        grading_thread.join()
        print(f"Saving Posture Test data under test name : {visualGlobals.testName}")
        print("Posture Graded")

