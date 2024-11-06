import cv2
import mediapipe as mp
import pygame
import time
import ctypes  # For window control

# Initialize MediaPipe hands and Pygame for audio
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=2, min_detection_confidence=0.8)
mp_drawing = mp.solutions.drawing_utils

pygame.mixer.init()
background_sound = pygame.mixer.Sound('./bg_sound.wav')  
sound_on = False

# Timer setup
MODES = ["Work", "Short Break", "Long Break"]
mode_durations = {"Work": 25 * 60 * 60, "Short Break": 5 * 60 * 60, "Long Break": 15 * 60 * 60}  
current_mode = 0
timer_running = False
focus_mode = False
time_left = mode_durations[MODES[current_mode]]
cooldown_time = 1.5
last_action_time = 0
window_open = True

# Utility Functions for Window Control
def minimize_window():
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 6)

def restore_window():
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 9)

# Timer Control Functions
def start_timer():
    global timer_running, time_left
    timer_running = True
    time_left = mode_durations[MODES[current_mode]]
    print(f"Timer started for {MODES[current_mode]}: {time_left // 60} minutes")

def stop_timer():
    global timer_running, time_left
    timer_running = False
    time_left = mode_durations[MODES[current_mode]]
    print("Timer stopped.")

def toggle_background_sound():
    global sound_on
    sound_on = not sound_on
    if sound_on:
        background_sound.play(loops=-1)
        print("Sound ON")
    else:
        background_sound.stop()
        print("Sound OFF")

# Function to handle updating the countdown timer
def update_timer():
    global time_left, timer_running, current_mode
    
    if timer_running:
        time_left -= 1
        if time_left <= 0:
            timer_running = False
            current_mode = (current_mode + 1) % len(MODES)  # Switch to next mode
            time_left = mode_durations[MODES[current_mode]]
            print(f"Mode switched to {MODES[current_mode]}")
            pygame.mixer.Sound.play(pygame.mixer.Sound('./alarm.wav'))  # Sound for timer end

# Functions to control the OpenCV window based on focus mode
def close_timer_window():
    global window_open
    window_open = False
    cv2.destroyAllWindows()

def open_timer_window():
    global window_open
    window_open = True

# Gesture Detection and Handling
def handle_gestures(landmarks, num_hands):
    global timer_running, current_mode, time_left, focus_mode, last_action_time, window_open
    
    current_time = time.time()
    if current_time - last_action_time < cooldown_time:
        return  # Avoid repeat actions due to cooldown

    if num_hands == 1:
        # Gesture: Thumbs Up = Start Timer (Single Hand)
        if is_thumb_up(landmarks[0]) and not timer_running:
            start_timer()
            last_action_time = current_time
        # Gesture: Thumbs Down = Stop Timer (Single Hand)
        elif is_thumb_down(landmarks[0]) and timer_running:
            stop_timer()
            last_action_time = current_time
        # Gesture: Touch Ear for Background Sound Toggle
        elif is_touching_ear(landmarks[0]):
            toggle_background_sound()
            last_action_time = current_time

    if num_hands == 2:
        # Gesture: Swipe (Both Hands, Index and Middle Fingers Together Moving to One Side)
        if is_two_finger_swipe(landmarks): # working respectably fine
            current_mode = (current_mode + 1) % len(MODES)
            time_left = mode_durations[MODES[current_mode]]
            print(f"Switched to {MODES[current_mode]} mode.")
            last_action_time = current_time

        # Gesture: + Sign with Both Hands = Add Time
        elif is_plus_sign(landmarks) and timer_running:
            time_left += 5 * 60
            print("Added 5 minutes.")
            last_action_time = current_time

        # Gesture: - Sign with Both Hands = Reduce Time
        elif is_minus_sign(landmarks) and timer_running and time_left > 5 * 60:
            time_left -= 5 * 60
            print("Reduced 5 minutes.")
            last_action_time = current_time

        # Gesture: Double V Sign = Toggle Focus Mode
        elif is_double_v_sign(landmarks):
            focus_mode = not focus_mode
            if focus_mode:
                minimize_window()
                close_timer_window()
                print("Focus mode ON")
            else:
                restore_window()
                open_timer_window()
                print("Focus mode OFF")
            last_action_time = current_time

# Gesture Functions for Recognizing Specific Gestures
def is_thumb_up(hand_landmarks):  # Keep this one as is - it's already intuitive
    return hand_landmarks[4].y < hand_landmarks[3].y < hand_landmarks[2].y < hand_landmarks[1].y

def is_thumb_down(hand_landmarks):  # Keep this one as is - it's already intuitive
    cnt = 0
    if hand_landmarks[4].y > hand_landmarks[3].y:
        cnt+=1
    if hand_landmarks[3].y > hand_landmarks[2].y:
        cnt+=1
    if hand_landmarks[2].y > hand_landmarks[1].y:
        cnt+=1
    return cnt >= 2

def is_two_finger_swipe(landmarks):
    """
    New gesture: Both hands making peace signs (V shape with index and middle fingers)
    This is more intuitive than just index fingers
    """
    if len(landmarks) != 2:
        return False
    
    for hand in landmarks:
        # Check for peace sign
        index_up = hand[8].y < hand[6].y  # Index extended
        middle_up = hand[12].y < hand[10].y  # Middle extended
        other_fingers_down = (hand[16].y > hand[14].y and  # Ring finger down
                            hand[20].y > hand[18].y)  # Pinky down
        
        if not (index_up and middle_up and other_fingers_down):
            return False
    
    # Hands should be at similar height
    hands_aligned = abs(landmarks[0][8].y - landmarks[1][8].y) < 0.1
    return hands_aligned

def is_plus_sign(landmarks):
    """
    New gesture: Both hands with all fingers extended (open palms)
    Much simpler than specific finger combinations
    """
    if len(landmarks) != 2:
        return False
    
    for hand in landmarks:
        # All fingers should be extended
        fingers_up = (
            hand[8].y < hand[6].y and   # Index up
            hand[12].y < hand[10].y and  # Middle up
            hand[16].y < hand[14].y and  # Ring up
            hand[20].y < hand[18].y      # Pinky up
        )
        if not fingers_up:
            return False
    
    # Hands should be at similar height and proper distance
    hands_aligned = abs(landmarks[0][8].y - landmarks[1][8].y) < 0.1
    proper_distance = 0.2 < abs(landmarks[0][8].x - landmarks[1][8].x) < 0.6
    
    return hands_aligned and proper_distance

def is_minus_sign(landmarks):
    """
    New gesture: Both hands in fists (all fingers closed)
    Much simpler than specific finger combinations
    """
    if len(landmarks) != 2:
        return False
    
    for hand in landmarks:
        # All fingers should be closed
        fingers_down = (
            hand[8].y > hand[6].y and   # Index down
            hand[12].y > hand[10].y and  # Middle down
            hand[16].y > hand[14].y and  # Ring down
            hand[20].y > hand[18].y      # Pinky down
        )
        if not fingers_down:
            return False
    
    # Hands should be at similar height and proper distance
    hands_aligned = abs(landmarks[0][8].y - landmarks[1][8].y) < 0.1
    proper_distance = 0.2 < abs(landmarks[0][8].x - landmarks[1][8].x) < 0.6
    
    return hands_aligned and proper_distance

def is_double_v_sign(landmarks):
    """
    New gesture: Both hands showing three fingers (index, middle, ring)
    More stable than checking for exact V positions
    """
    if len(landmarks) != 2:
        return False
    
    for hand in landmarks:
        three_fingers_up = (
            hand[8].y < hand[6].y and   # Index up
            hand[12].y < hand[10].y and  # Middle up
            hand[16].y < hand[14].y and  # Ring up
            hand[20].y > hand[18].y      # Pinky down
        )
        if not three_fingers_up:
            return False
    
    return True

def is_touching_ear(hand_landmarks):
    """
    New gesture: Simple phone gesture with just thumb and pinky extended
    Removed the height requirement to make it easier to perform
    """
    # Check if thumb and pinky are extended
    thumb_extended = hand_landmarks[4].y < hand_landmarks[2].y
    pinky_extended = hand_landmarks[20].y < hand_landmarks[18].y
    
    # Check if other fingers are closed
    other_fingers_closed = (
        hand_landmarks[8].y > hand_landmarks[6].y and   # Index closed
        hand_landmarks[12].y > hand_landmarks[10].y and # Middle closed
        hand_landmarks[16].y > hand_landmarks[14].y     # Ring closed
    )
    
    return thumb_extended and pinky_extended and other_fingers_closed

# Main loop for gesture control and timer
def main():
    cap = cv2.VideoCapture(0)
    
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            print("Ignoring empty camera frame.")
            continue
        
        # Flip frame and process it for hand detection
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb_frame)
        
        landmarks = []
        if result.multi_hand_landmarks:
            for hand_landmarks in result.multi_hand_landmarks:
                landmarks.append(hand_landmarks.landmark)
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
        
        handle_gestures(landmarks, len(landmarks))
        
        # Display remaining time on frame
        mins, secs = divmod(time_left, 60)
        cv2.putText(frame, f"{MODES[current_mode]}: {mins:02d}:{secs:02d}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
        
        # Show the frame with detected hand and timer if window is open
        if window_open:
            cv2.imshow("Pomodoro Timer", frame)
        
        # Countdown timer
        update_timer()
        
        # Exit loop on pressing 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    background_sound.stop()

if __name__ == "__main__":
    main()
