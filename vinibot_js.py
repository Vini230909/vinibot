Timer.instance().clear();

const filePath = "C:/Users/vini2/PycharmProjects/vinibot/response_log.txt";
let lastMessageTime = 0;
const COOLDOWN = 1000;

function processAndDeleteLine() {
    try {
        const file = new java.io.File(filePath);
        if (!file.exists()) return;

        const lines = java.nio.file.Files.readAllLines(file.toPath());
        if (lines.isEmpty()) return;

        const currentTime = Time.millis();
        if (currentTime - lastMessageTime >= COOLDOWN) {
            const lastLine = lines.remove(lines.size() - 1);
            Call.sendChatMessage(lastLine);
            lastMessageTime = currentTime;

            java.nio.file.Files.write(file.toPath(), lines);
        }
    } catch (e) {
    }
}

Timer.schedule(() => processAndDeleteLine(), 0, 1/72);
