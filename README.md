# DAMRIku Bus Ticket Booking Application

Welcome to DAMRIku, a simple web application for bus ticket booking, built with Flask (Python) for the backend and HTML/CSS/JavaScript for the frontend. This project also integrates with Google Firestore for data storage and includes performance analysis tools to compare cloud (Firestore) vs. local (JSON file) data delivery.

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation and Setup](#installation-and-setup)
- [Running the Application](#running-the-application)
- [Performance Analysis](#performance-analysis)
- [Important Note on Firebase Credentials](#important-note-on-firebase-credentials)
- [Contributing](#contributing)
- [License](#license)

## Features

-   **Bus List**: View available DAMRI bus routes with details.
-   **Ticket Booking Form**: Book bus tickets by providing passenger details, selecting a bus route, and specifying seats.
-   **Local & Cloud Storage**: Data is saved concurrently to a local JSON file and a Google Firestore database.
-   **Performance Analysis**:
    -   Measure and display latency for individual booking operations (Firestore vs. Local).
    -   Run simulated stress tests to evaluate average latency and throughput for bulk operations.
    -   Visualize latency per iteration using interactive charts.

## Project Structure
![image](https://github.com/user-attachments/assets/20d6b439-c3c0-40a1-ab31-739287a79b1e)


## Prerequisites

Before you begin, ensure you have the following installed:

-   **Python 3.8+**: [Download Python](https://www.python.org/downloads/)
-   **Git**: [Download Git](https://git-scm.com/downloads)
-   **Google Cloud Project / Firebase Project**: You need a Firebase project with a Firestore database enabled.
    -   **Firebase Admin SDK Private Key**: A JSON key file for your Firebase Service Account. See [Firebase documentation](https://firebase.google.com/docs/admin/setup) on how to generate this key. **This file (`firebase_key.json`) should NEVER be committed to a public repository.**

## Installation and Setup

Follow these steps to get the project up and running on your local machine:

1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git](https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git)
    cd YOUR_REPO_NAME/damriku_app
    ```
    *(Replace `YOUR_USERNAME` and `YOUR_REPO_NAME` with your actual GitHub username and repository name)*

2.  **Create a Virtual Environment:**
    It's highly recommended to use a virtual environment to manage project dependencies.
    ```bash
    python -m venv venv
    ```

3.  **Activate the Virtual Environment:**
    -   **Windows:**
        ```bash
        .\venv\Scripts\activate
        ```
    -   **macOS/Linux:**
        ```bash
        source venv/bin/activate
        ```

4.  **Install Dependencies:**
    Install the required Python packages using pip.
    ```bash
    pip install -r requirements.txt
    ```
    *(If `requirements.txt` is not present yet, you can create it by running `pip freeze > requirements.txt` after installing Flask and firebase-admin manually, i.e., `pip install Flask firebase-admin`)*

5.  **Place Firebase Service Account Key:**
    **This is crucial.** Obtain your Firebase Service Account private key file (a JSON file) from your Firebase Console (Project settings > Service accounts > Generate new private key).
    **Rename this downloaded file to `serviceAccountKey.json`** and place it directly inside the `damriku_app/` directory (the same directory as `app.py`).
    **WARNING**: Ensure this file is listed in your `.gitignore` to prevent accidentally pushing it to GitHub.

## Running the Application

1.  **Ensure your virtual environment is active.**
2.  **Navigate to the `damriku_app/` directory** if you are not already there.
3.  **Run the Flask application:**
    ```bash
    flask run
    ```
    or
    ```bash
    python app.py
    ```

4.  **Access the Application:**
    Open your web browser and go to: `http://127.0.0.1:5000/`

## Performance Analysis

Navigate to the "Hasil Pengukuran" (Measurement Results) page within the application to:

-   View a graph of latency comparisons for individual user bookings (Firestore vs. Local JSON).
-   Run simulated stress tests by specifying the number of iterations.
-   Observe average latency, minimum/maximum latency, and throughput (operations per second) for both storage methods under load.
-   Analyze detailed latency per iteration via a dedicated graph.

## Important Note on Firebase Credentials

This application uses a Firebase Service Account Key (`serviceAccountKey.json`) to authenticate and interact with Firestore from the Flask backend.

**For security reasons, this `serviceAccountKey.json` file is highly sensitive and should NEVER be exposed publicly or committed to your GitHub repository.** It grants administrative access to your Firebase project.

If you wish to deploy this application for public access, you **must not** host it purely as static pages on platforms like GitHub Pages. Instead, you would need to:
1.  **Deploy your Flask backend** to a secure server environment (e.g., Google App Engine, Google Cloud Run, Heroku, AWS Elastic Beanstalk) where the `serviceAccountKey.json` can be kept securely.
2.  Alternatively, if you want direct frontend-to-Firestore interaction, you would need to refactor the frontend to use the **Firebase JavaScript Client SDK** and implement **strict Firebase Security Rules** to manage access.

## Contributing

Feel free to fork this repository, submit pull requests, or open issues if you find any bugs or have suggestions for improvements.
