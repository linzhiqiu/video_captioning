import streamlit as st
from openai import OpenAI
from streamlit_feedback import streamlit_feedback
import os
import json
from datetime import datetime
from sample_captions import SAMPLE_CAPTIONS

# Initialize session state for API key and OpenAI client
if 'api_key' not in st.session_state:
    st.session_state.api_key = None

def save_feedback_data(video_id, data):
    """Save feedback data to a JSON file"""
    os.makedirs('outputs', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'outputs/{video_id}_{timestamp}.json'
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)
    
    return filename

# List of video URLs
VIDEO_URLS = [
    "https://dqs0aptimu8jn.cloudfront.net/Gel59Iy3YhQ.0.3.mp4",
    "https://dqs0aptimu8jn.cloudfront.net/GdRJCTR1KDQ.0.6.mp4",
    "https://huggingface.co/datasets/Rapidata/sora-video-generation-aligned-words/blob/main/Videos/017_20250114_sora.mp4"
]

def get_video_id(url):
    return url.split('/')[-1]

def load_instructions():
    with open('instructions.txt', 'r') as f:
        return f.read()

def load_prompt(filename, **kwargs):
    with open(f'prompts/{filename}', 'r') as f:
        prompt = f.read()
    return prompt.format(**kwargs)

def get_gpt4_feedback(feedback, original_caption):
    prompt = load_prompt('feedback_prompt.txt', 
                        original_caption=original_caption,
                        feedback=feedback)
    
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    
    return response.choices[0].message.content.strip()

def get_gpt4_caption(feedback, original_caption):
    prompt = load_prompt('caption_prompt.txt',
                        original_caption=original_caption,
                        feedback=feedback)
    
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    
    return response.choices[0].message.content.strip()

def main():
    st.title("Video Caption Feedback System")
    
    # Debug information
    st.sidebar.write(f"Current Step: {st.session_state.get('current_step', 0)}")
    if 'feedback_data' in st.session_state:
        st.sidebar.write("Feedback Data Keys:", list(st.session_state.feedback_data.keys()))
    
    # API Key input
    api_key = st.text_input("Enter your OpenAI API Key:", type="password")
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
        st.session_state.api_key = api_key
    
    if not st.session_state.api_key:
        st.warning("Please enter your OpenAI API key to proceed.")
        return
    
    # Session state initialization
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 0
    if 'feedback_data' not in st.session_state:
        st.session_state.feedback_data = {}
    if 'submit_feedback_clicked' not in st.session_state:
        st.session_state.submit_feedback_clicked = False
    if 'submit_caption_clicked' not in st.session_state:
        st.session_state.submit_caption_clicked = False
        
    def on_feedback_submit():
        st.session_state.submit_feedback_clicked = True
        
    def on_caption_submit():
        st.session_state.submit_caption_clicked = True
    
    # Select video
    selected_video = st.selectbox("Select a video:", VIDEO_URLS)
    video_id = get_video_id(selected_video)
    
    # Display video
    st.video(selected_video)
    
    # Display instructions
    st.subheader("Instructions")
    st.write(load_instructions())
    
    # Display original caption
    st.subheader("Current Caption")
    original_caption = SAMPLE_CAPTIONS.get(video_id, "No caption available")
    st.write(original_caption)
    
    # Display conversation history
    if st.session_state.feedback_data:
        st.subheader("Conversation History")
        if "initial_feedback" in st.session_state.feedback_data:
            st.markdown("**Your Initial Feedback:**")
            st.write(st.session_state.feedback_data["initial_feedback"])
        
        if "gpt_feedback" in st.session_state.feedback_data:
            st.markdown("**AI-Polished Feedback:**")
            st.write(st.session_state.feedback_data["gpt_feedback"])
        
        if "final_feedback" in st.session_state.feedback_data:
            st.markdown("**Final Feedback:**")
            st.write(st.session_state.feedback_data["final_feedback"])
        
        if "gpt_caption" in st.session_state.feedback_data:
            st.markdown("**AI-Improved Caption:**")
            st.write(st.session_state.feedback_data["gpt_caption"])
        
        if "final_caption" in st.session_state.feedback_data:
            st.markdown("**Final Caption:**")
            st.write(st.session_state.feedback_data["final_caption"])
    
    # Step 0: Get initial user feedback
    if st.session_state.current_step == 0:
        user_feedback = st.text_area("Please provide your feedback on this caption:")
        
        if st.button("Submit Initial Feedback") and user_feedback:
            # Initialize feedback data
            st.session_state.feedback_data = {
                "video_id": video_id,
                "original_caption": original_caption,
                "initial_feedback": user_feedback,
                "timestamp": datetime.now().isoformat()
            }
            
            # Get GPT-4 polished feedback
            gpt_feedback = get_gpt4_feedback(user_feedback, original_caption)
            st.session_state.feedback_data["gpt_feedback"] = gpt_feedback
            st.session_state.current_step = 1
            st.rerun()
    
    # Step 1: Rate GPT's feedback and optionally provide corrected feedback
    elif st.session_state.current_step == 1:
        st.subheader("Rate AI-Polished Feedback")

        # Fetch stored feedback rating if it exists
        if "feedback_rating" in st.session_state:
            score = st.session_state.feedback_rating
        else:
            feedback_response = streamlit_feedback(
                feedback_type="faces",
                key="feedback_faces"
            )

            if feedback_response and 'score' in feedback_response:
                st.session_state.feedback_rating = feedback_response['score']
                score = feedback_response['score']
            else:
                score = None  # Default to None if no response yet

        if score:
            st.session_state.feedback_data["feedback_rating"] = score  # Store in feedback data

            if score != "😀":
                st.write("Please modify the feedback below:")

                # Ensure final_feedback is stored persistently
                if "final_feedback" not in st.session_state:
                    st.session_state.final_feedback = st.session_state.feedback_data["gpt_feedback"]

                final_feedback = st.text_area(
                    "Correct feedback:",
                    value=st.session_state.final_feedback,
                    key="correct_feedback"
                )

                # Button Click Handling
                if st.button("Submit Corrected Feedback"):
                    print("Button clicked")
                    if final_feedback.strip():
                        # Persist final feedback
                        st.session_state.feedback_data["final_feedback"] = final_feedback
                        st.session_state.final_feedback = final_feedback
                        
                        # Store step change in session state
                        st.session_state.current_step = 2
                        st.session_state.feedback_submitted = True  # Flag to track submission

                        st.rerun()  # Force rerun
                    else:
                        st.warning("Please provide a corrected feedback before submitting.")
                        st.rerun()
            else:
                # If rating is happy, then directly use the GPT feedback as final feedback
                st.session_state.feedback_data["final_feedback"] = st.session_state.feedback_data["gpt_feedback"]
                st.session_state.current_step = 2
                st.session_state.feedback_submitted = True  # Flag to track submission

        # Ensure we move to the next step on rerun
        if st.session_state.get("feedback_submitted", False):
            st.session_state.feedback_submitted = False  # Reset flag
            st.session_state.current_step = 2  # Ensure next step persists
            st.rerun()




    
    # Step 2: Generate caption (intermediate step)
    elif st.session_state.current_step == 2:
        # Get the final feedback (either corrected or GPT's version)
        final_feedback = st.session_state.feedback_data["final_feedback"]
        # Get improved caption
        gpt_caption = get_gpt4_caption(final_feedback, original_caption)
        st.session_state.feedback_data["gpt_caption"] = gpt_caption
        # Move to caption rating step
        st.session_state.current_step = 3
        st.rerun()
    
    # Step 3: Rate GPT's caption and optionally provide corrected caption
    elif st.session_state.current_step == 3:
        st.subheader("Rate AI-Improved Caption")
        st.write(st.session_state.feedback_data["gpt_caption"])

        # Retrieve stored caption rating if it exists
        if "caption_rating" in st.session_state:
            score = st.session_state.caption_rating
        else:
            caption_response = streamlit_feedback(
                feedback_type="faces",
                key="caption_faces"
            )

            if caption_response and 'score' in caption_response:
                st.session_state.caption_rating = caption_response['score']
                score = caption_response['score']
            else:
                score = None  # Default to None if no response yet

        if score:
            st.session_state.feedback_data["caption_rating"] = score  # Persist rating

            if score != "😀":
                st.write("Please modify the caption below:")

                # Ensure final_caption is stored persistently
                if "final_caption" not in st.session_state:
                    st.session_state.final_caption = st.session_state.feedback_data["gpt_caption"]

                final_caption = st.text_area(
                    "Correct caption:",
                    value=st.session_state.final_caption,
                    key="correct_caption"
                )

                # Button Click Handling
                if st.button("Submit Final Caption"):
                    if final_caption.strip():
                        # Persist final caption
                        st.session_state.feedback_data["final_caption"] = final_caption
                        st.session_state.final_caption = final_caption
                        
                        # Save feedback data
                        filename = save_feedback_data(st.session_state.feedback_data["video_id"], st.session_state.feedback_data)
                        st.success(f"Feedback saved successfully to {filename}")

                        # Reset session state for new feedback cycle
                        st.session_state.current_step = 0
                        st.session_state.feedback_data = {}
                        st.session_state.caption_rating = None  # Clear rating state
                        st.rerun()

            else:
                # If rating is happy, finalize caption and save
                st.session_state.feedback_data["final_caption"] = st.session_state.feedback_data["gpt_caption"]
                filename = save_feedback_data(st.session_state.feedback_data["video_id"], st.session_state.feedback_data)
                st.success(f"Feedback saved successfully to {filename}")

                # Reset session state for new feedback cycle
                st.session_state.current_step = 0
                st.session_state.feedback_data = {}
                st.session_state.caption_rating = None  # Clear rating state
                st.rerun()


if __name__ == "__main__":
    main()