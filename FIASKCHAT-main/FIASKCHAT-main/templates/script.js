document.addEventListener('DOMContentLoaded', () => {
  const emojiBtn = document.getElementById('emojiBtn'); 
  const emojiContainer = document.getElementById('emojiContainer'); 
  const messageInput = document.getElementById('messageInput'); 
  const sendMessageBtn = document.getElementById('sendMessageBtn'); 
  const messages = document.getElementById('messages'); // Chat messages container

  // Toggle emoji picker visibility
  emojiBtn.addEventListener('click', () => {
    emojiContainer.style.display = emojiContainer.style.display === 'none' ? 'flex' : 'none';
  });

  // Insert emoji into input when clicked
  document.querySelectorAll('.emoji-btn').forEach(button => {
    button.addEventListener('click', () => {
      messageInput.value += button.textContent;
      emojiContainer.style.display = 'none';
      messageInput.focus();
    });
  });

  // Function to send message to server
  const sendMessage = () => {
    const msg = messageInput.value.trim();
    if (!msg) return; // don't send empty messages
    socketio.emit('message', { data: msg });
    messageInput.value = '';
  };

  // Send message on button click
  sendMessageBtn.addEventListener('click', sendMessage);

  // Send message on Enter key press
  messageInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      sendMessage();
    }
  });

  // Listen for incoming messages from server and display them
  socketio.on('message', data => {
    if (!data.name || !data.message) return;

    // Turn URLs into clickable links
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    const formattedMsg = data.message.replace(urlRegex, '<a href="$&" target="_blank" rel="noopener noreferrer">$&</a>');

    // Create message div and append
    const div = document.createElement('div');
    div.classList.add('text');
    div.innerHTML = `<span><strong>${data.name}</strong>: ${formattedMsg}</span> <span class="muted">${new Date().toLocaleString()}</span>`;
    messages.appendChild(div);

    // Scroll to bottom on new message
    messages.scrollTop = messages.scrollHeight;
  });
});
