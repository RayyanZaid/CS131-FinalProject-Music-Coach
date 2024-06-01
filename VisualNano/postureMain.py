import cv2

# To get angles between joints
import mediapipe as mp


import numpy as np

import cloud

import visualGlobals

# MediaPipe drawing utility
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_pose = mp.solutions.pose


# main function for posture grading video stream
    # 1) while loop that records user
    # 2) use mediapipe to get joints
    # 3) calculate angles to keep track of posture

def process_feedback(feedback_conditions, leg_position_angle, neck_posture_angle, sitting_posture_angle, frame, numFrame, fps):
    numFeedbackPointersPerFrame = 0
    feedbackString = ""
    feedbackImage = None

    # Iterate over each condition in the dictionary
    for key, details in feedback_conditions.items():
        # Check the condition and append feedback if necessary
        moreThan3Seconds = (numFrame - details['lastFrame']) / fps > 180

        if 'leg' in key and moreThan3Seconds:
            if details['condition'](leg_position_angle) and leg_position_angle != None:
                numFeedbackPointersPerFrame += 1
                feedbackString += f"{numFeedbackPointersPerFrame}. {details['message']} \n"
                feedbackImage = frame
                feedback_conditions[key]['lastFrame'] = numFrame

        elif 'neck' in key and moreThan3Seconds and neck_posture_angle != None:
            if details['condition'](neck_posture_angle):
                numFeedbackPointersPerFrame += 1
                feedbackString += f"{numFeedbackPointersPerFrame}. {details['message']} \n"
                feedbackImage = frame
                feedback_conditions[key]['lastFrame'] = numFrame

        elif 'back' in key and moreThan3Seconds and sitting_posture_angle != None:
            if details['condition'](sitting_posture_angle):
                numFeedbackPointersPerFrame += 1
                feedbackString += f"{numFeedbackPointersPerFrame}. {details['message']} \n"
                feedbackImage = frame
                feedback_conditions[key]['lastFrame'] = numFrame

    return feedbackString, feedbackImage



def postureGrading():

    cap = cv2.VideoCapture(0)
    
    fps = cap.get(cv2.CAP_PROP_FPS)

    if not cap.isOpened():
        print("Error: Could not open video stream")
        return


    # Variable to keep track of testing status. 
    # Will recieve signal from other Nano to switch testingFinished = True
    testingFinished = False
    # For debugging, let's say testingFinished = True after 300 frames


    # Variable to detect if user says "Stop"
    userInterruptedTesting = False


    sittingPostureGrade = 0
    neckPostureGrade = 0
    legPositionGrade = 0

    
    # list of feedback strings to images
    feedbackArray : list[tuple[str : np.ndarray]] = []


    numFrames = 0

    # neckArray = []
    # legArray = []
    feedback_conditions = {
    'leg_too_far': {
        'condition': lambda angle: angle > 106,
        'message': "Bring your feet closer to the chair. Feet are too far in front of you.",
        'lastFrame' : -10000
    },
    'leg_too_close': {
        'condition': lambda angle: angle < 75,
        'message': "Your feet are underneath the chair. Please bring them forward.",
        'lastFrame' : -10000,
    },
    'neck_too_down': {
        'condition': lambda angle: angle < 125,
        'message': "You are pointed too downwards. Lift your neck and point your instrument forward (parallel to the ground).",
        'lastFrame' : -10000,
    },
    'neck_too_up': {
        'condition': lambda angle: angle > 160,
        'message': "You are pointed too upwards. Bring your neck down.",
        'lastFrame' : -10000,
    },
    'back_too_hunched': {
        'condition': lambda angle: angle < 80,
        'message': "You are too hunched forward. Sit back and try to make your back straight.",
        'lastFrame' : -10000,
    },
    'back_too_leaned_back': {
        'condition': lambda angle: angle > 110,
        'message': "You are too leaned back. Sit up and try to make your back straight.",
        'lastFrame' : -10000,
    },
}
    

    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        while cap.isOpened():
            
            numFrames += 1

            if numFrames == 51:
                testingFinished = True

            interruptionForDebugging = cv2.waitKey(1) and 0xFF == ord('q')

            if interruptionForDebugging:
                print("In Debug")

            if  userInterruptedTesting:
                print("Do not keep results of this rest")
                break

            if testingFinished:
                sittingPostureGrade /= numFrames
                neckPostureGrade /= numFrames
                legPositionGrade /= numFrames

                print(f"Sitting Posture Grade : {sittingPostureGrade}")
                print(f"Neck Posture Grade : {neckPostureGrade}")
                
                print(f"Leg Position Grade : {legPositionGrade}")


                print("Need to calculate score here and send pictures of posture to database")
 
                
                wrapUpTesting(sittingPostureGrade, neckPostureGrade, legPositionGrade,feedbackArray,visualGlobals.testName)
                break
                
            success, frame = cap.read()
            if not success:
                print("Error: Frame not available. Video has finished or is corrupt")
                break

            # Convert the BGR image to RGB for mediapipe cuz it cv2 uses BGR
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Process the image and detect the pose
            results = pose.process(frame_rgb)

            # Draw the pose annotations on the frame.
            mp_drawing.draw_landmarks(
                frame,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style())



        # If no end cases run, then perform calculations
            # Display the frame. Might delete this later (just for debugging)
            cv2.imshow('Video Stream', frame)

            sitting_posture_angle, neck_posture_angle, leg_position_angle = get_pose_estimation(frame,pose)
            
            # if holding_posture_angle > 120:
            #     print('bruh')
            # print(f"Sitting Posture : {sitting_posture_angle}")
            # print(f"Holding Posture : {holding_posture_angle}")
            # print(f"Leg Position : {leg_position_angle}")

            sittingPostureGrade += gradePostureForEachFrame(sitting_posture_angle, sittingPostureDict)
            neckPostureGrade += gradePostureForEachFrame(neck_posture_angle, neckPostureDict)
            legPositionGrade += gradePostureForEachFrame(leg_position_angle, legPositionDict)

            print(legPositionGrade)
            # neckArray.append(neck_posture_angle)
            # legArray.append(leg_position_angle)

            
            # TODO: Give Feedback


            if len(feedbackArray) < 6:
                feedbackString , feedbackImage = process_feedback(feedback_conditions, leg_position_angle, neck_posture_angle, sitting_posture_angle, frame, numFrames, fps)

                if len(feedbackString) > 0:
                    feedbackArray.append((feedbackString,feedbackImage))


    print("Done with posture grading")




            

    cap.release()
    cv2.destroyAllWindows()

def calculate_angle(a, b, c):
    a = np.array(a)  # First point
    b = np.array(b)  # Middle point
    c = np.array(c)  # End point
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians*180.0/np.pi)
    if angle > 180.0:
        angle = 360-angle
    return angle

def get_pose_estimation(image, pose):
    results = pose.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    if not results.pose_landmarks:
        return None, None, None

    landmarks = results.pose_landmarks.landmark

    sitting_posture = calculate_angle(
        [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].x, landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].y],
        [landmarks[mp_pose.PoseLandmark.LEFT_HIP].x, landmarks[mp_pose.PoseLandmark.LEFT_HIP].y],
        [landmarks[mp_pose.PoseLandmark.LEFT_KNEE].x, landmarks[mp_pose.PoseLandmark.LEFT_KNEE].y]
    )

    # Calculate specific angles from the landmarks
    neck_posture = calculate_angle(
        [landmarks[mp_pose.PoseLandmark.NOSE].x, landmarks[mp_pose.PoseLandmark.NOSE].y],
        [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].x, landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].y],
        [landmarks[mp_pose.PoseLandmark.LEFT_HIP].x, landmarks[mp_pose.PoseLandmark.LEFT_HIP].y]
    )



    leg_position = calculate_angle(
        [landmarks[mp_pose.PoseLandmark.LEFT_HIP].x, landmarks[mp_pose.PoseLandmark.LEFT_HIP].y],
        [landmarks[mp_pose.PoseLandmark.LEFT_KNEE].x, landmarks[mp_pose.PoseLandmark.LEFT_KNEE].y],
        [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE].x, landmarks[mp_pose.PoseLandmark.LEFT_ANKLE].y]
    )

    

    return sitting_posture, neck_posture, leg_position


# ChatGPT generated

# ChatGPT Prompt:  create a 2-tuple : int dictionary where highest grade range set from 85 to 100, where the grade is 100%. 
# From this range, decrement grade by 5 points for each 5-degree decrease until we reach a grade of 60. 
# Angles outside of the ranges specified will be graded as 0.

sittingPostureDict = {

    (90, 100): 100,


    (85, 89): 90,
    (80, 84): 80,
    (75, 79): 70,
    (70, 74): 60,
    (65, 69): 50,
    (60, 64): 40,
    (0, 59) :  0,


    (101, 105): 90,
    (106, 110): 80,
    (111, 115): 70,
    (116, 120): 60,
    (121, 125): 50,
    (126, 130): 40,
    (130, 180):  0,
}

# Define the holding posture dictionary with detailed ranges
neckPostureDict = {
    (145, 155): 100,

    (130, 144): 95,
    (125, 129): 85,
    (120, 124): 75,
    (115, 119): 65,
    (100, 114): 50,
    (0,    99):  0,

    (156, 160) : 95,
    (161, 165) : 90,
    (166, 170) : 80,
    (171, 180) : 70,

}



legPositionDict = {
    (75, 95): 100,
    (70, 74): 80,
    (65, 69): 75,
    (60, 64): 70,
    (55, 59): 65,
    (50, 54): 60,
    (0, 44) : 0,


    (96, 100): 95,
    (101, 105): 90,
    (106, 110): 80,
    (111, 115): 70,
    (116, 125): 60,
    (126, 180): 0,
}


def gradePostureForEachFrame(angle, angleRangeToGrade):

    if angle == None:
        return 0
    for (low, high), grade in angleRangeToGrade.items():
        if low <= angle <= high:
            return grade
        
    return 0



def wrapUpTesting(sittingPostureGrade, neckPostureGrade, legPositionGrade, feedbackArray, testName):

    # Calculate Final Weighted Grade

    # Most important is Sitting, then Holding, then Leg
    
    finalGrade = 0.4 * sittingPostureGrade + 0.35 * neckPostureGrade + 0.25 * legPositionGrade

    # Send Feedback and Grade to Cloud Database
    cloud.store_grade_with_files("user1", testName, finalGrade, feedbackArray)

if __name__ == '__main__':
    postureGrading()
