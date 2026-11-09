import greetingBot from "../assets/nexo-wave-bot.webp";

export default function AuthMascot() {
  return (
    <div className="auth-mascot" aria-label="Robot de Nexo Laboral saludando">
      <img src={greetingBot} alt="" />
      <span>¡Hola! Qué bueno verte</span>
    </div>
  );
}
