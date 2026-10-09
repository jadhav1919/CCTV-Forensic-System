\# CCTV Video Forensic Event Detection and Automated Summarization System



\## 1. Project Overview



This project analyzes CCTV footage to detect people entering a predefined restricted area. It records event timestamps, captures snapshots, extracts short video clips, and provides a dashboard to review the detected events.



\## 2. Objectives



\- Automate CCTV video analysis.

\- Detect people entering a predefined restricted region.

\- Record event timestamps and tracked object IDs.

\- Generate snapshots and short event clips.

\- Create a summarized view of detected events.

\- Maintain evidence logs and generate forensic reports.



\## 3. Features



\- CCTV video upload

\- Person detection using YOLO

\- Object tracking using ByteTrack

\- Restricted-area entry detection

\- Event logging in CSV format

\- Evidence snapshots and event clips

\- Video summary generation

\- Interactive Streamlit dashboard

\- Report and evidence export



\## 4. Technology Stack



\- Python

\- OpenCV

\- YOLO (Ultralytics)

\- ByteTrack

\- Streamlit

\- FFmpeg

\- Pandas



\## 5. Project Structure



```text

CCTV-Forensic-System/

├── src/

│   ├── app.py

│   └── process\_video.py

├── data/

├── models/

├── outputs/

├── videos/

├── requirements.txt

├── .gitignore

└── README.md

```



\## 6. Installation



Clone the repository:



```bash

git clone https://github.com/jadhav1919/CCTV-Forensic-System.git

cd CCTV-Forensic-System

```



Create and activate a virtual environment:



```bash

python -m venv venv

```



On Windows:



```cmd

venv\\Scripts\\activate

```



Install dependencies:



```bash

pip install -r requirements.txt

```



\## 7. Run the Application



Start the Streamlit dashboard:



```bash

streamlit run src/app.py

```



Follow the dashboard instructions to upload and analyze CCTV footage.



\## 8. Detection Scope



The current implementation detects people entering a predefined restricted region. It does not automatically classify every type of suspicious activity or establish criminal intent.



\## 9. Dataset and Evidence



Input videos and generated forensic evidence are not included in this repository by default. Use appropriately licensed datasets and follow their usage conditions.



\## 10. Project Purpose



This is an academic project developed to demonstrate video analysis, event detection, evidence organization, and automated reporting for multimedia forensics.

