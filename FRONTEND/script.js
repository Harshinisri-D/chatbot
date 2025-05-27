async function sendMessage() {
    const userInput = document.getElementById('chat-input').value;
    const chatOutput = document.getElementById('chat-output');

    if (userInput.trim() === '') {
        alert('Please type a message.');
        return;
    }

    // Display user's message in chat
    const userMessage = document.createElement('p');
    userMessage.textContent = `You: ${userInput}`;
    userMessage.style.color = 'blue';
    chatOutput.appendChild(userMessage);

    try {
        const response = await fetch('http://127.0.0.1:5000/response', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query: userInput }),
        });

        const data = await response.json();
        const botMessage = document.createElement('p');

        // ✅ Handle "end chat" scenario (Only show score & feedback)
        if (userInput.toLowerCase() === "end chat") {
            if (data.score !== undefined && data.feedback !== undefined) {
                botMessage.textContent = `Chat ended. Here is your evaluation:`;
                chatOutput.appendChild(botMessage);

                // Display Score
                const scoreMessage = document.createElement('p');
                scoreMessage.textContent = `⭐ Score: ${data.score}/10`;
                scoreMessage.style.color = 'green';
                chatOutput.appendChild(scoreMessage);

                // Display Feedback
                const feedbackMessage = document.createElement('p');
                feedbackMessage.textContent = `📌 Feedback: ${data.feedback}`;
                feedbackMessage.style.color = 'purple';
                chatOutput.appendChild(feedbackMessage);
            } else {
                botMessage.textContent = `Bot: An error occurred while processing your evaluation.`;
                chatOutput.appendChild(botMessage);
            }
        } else {
            // ✅ Normal bot response flow
            if (data.response) {
                botMessage.textContent = `Bot: ${data.response}`;
            } else {
                botMessage.textContent = `Bot: Something went wrong.`;
            }
            chatOutput.appendChild(botMessage);
        }

    } catch (error) {
        const errorMessage = document.createElement('p');
        errorMessage.textContent = 'Error: Unable to connect to the server.';
        chatOutput.appendChild(errorMessage);
    }

    chatOutput.scrollTop = chatOutput.scrollHeight;
    document.getElementById('chat-input').value = '';
}

// ✅ Attach event listener to "Send" button
document.getElementById('send-btn').addEventListener('click', sendMessage);

// ✅ Attach event listener to "Enter" key for sending messages
document.getElementById('chat-input').addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
        event.preventDefault(); // Prevents new line in textarea
        sendMessage();
    }
});
