import ChatInput from "./chatInput";
import ChatMessage from "./messageBubble";

import baktiLogo from "../assets/bakti.png";

export default function ChatWindow({
  chat,
  sendMessage,
  userName,
}) {
  const greetingText = userName
    ? `Halo ${userName}! Ada yang bisa saya bantu hari ini?`
    : "Halo! Ada yang bisa saya bantu hari ini?";

  return (
    <div className="chat-container">

      <div className="chat-header">

        <img
          src={baktiLogo}
          className="logo"
          alt=""
        />

        <h2>Assistant</h2>

      </div>

      <div className="chat-body">
        <img
            src={baktiLogo}
            className="watermark"
            alt=""
        />

        {!chat && (
          <p className="empty-state">
            Belum ada percakapan yang dipilih. Klik "+ Percakapan Baru" di sidebar untuk mulai chat.
          </p>
        )}

        {chat && chat.messages?.length === 0 && (
          <ChatMessage
            sender="bot"
            text={greetingText}
          />
        )}

        {chat?.messages?.map((msg,index)=>(

            <ChatMessage
                key={index}
                sender={msg.sender}
                text={msg.text}
                loading={msg.loading}
            />

        ))}

    </div>

      <ChatInput sendMessage={sendMessage} disabled={!chat} />

    </div>
  );
}