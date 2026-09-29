<template>
    <div class="chat-sidebar" :class="{ open: visible }">
        <div class="chat-header">
            <span>💬 AI 助手</span>
            <button class="close-btn" @click="close">&times;</button>
        </div>
        <div class="chat-messages" ref="messagesContainer">
            <div v-for="(msg, idx) in messages" :key="idx" class="message" :class="msg.role">
                <div class="avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
                <div class="content" v-html="formatMessage(msg.content)"></div>
            </div>
            <div v-if="loading" class="message assistant">
                <div class="avatar">🤖</div>
                <div class="content typing">正在输入...</div>
            </div>
        </div>
        <div class="chat-input">
            <input type="text" v-model="inputMessage" placeholder="输入您的问题..." @keyup.enter="sendMessage"
                :disabled="loading" />
            <button @click="sendMessage" :disabled="loading || !inputMessage.trim()">
                发送
            </button>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch } from 'vue';
import * as api from '@/api';

const props = defineProps<{ visible: boolean }>();
const emit = defineEmits(['update:visible']);

const messages = ref<{ role: 'user' | 'assistant'; content: string }[]>([]);
const inputMessage = ref('');
const loading = ref(false);
const messagesContainer = ref<HTMLElement | null>(null);

const close = () => emit('update:visible', false);

const formatMessage = (text: string) => {
    // 支持简单的 Markdown 换行
    return text.replace(/\n/g, '<br />');
};

const scrollToBottom = async () => {
    await nextTick();
    if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    }
};

const sendMessage = async () => {
    const msg = inputMessage.value.trim();
    if (!msg || loading.value) return;
    inputMessage.value = '';
    messages.value.push({ role: 'user', content: msg });
    loading.value = true;
    await scrollToBottom();
    try {
        const res = await api.chat(msg);
        messages.value.push({ role: 'assistant', content: res.reply });
    } catch (e: any) {
        messages.value.push({ role: 'assistant', content: '抱歉，AI 服务暂时不可用，请稍后重试。' });
    } finally {
        loading.value = false;
        await scrollToBottom();
    }
};

watch(() => props.visible, (newVal) => {
    if (newVal) {
        // 打开时滚动到底部
        scrollToBottom();
    }
});
</script>

<style scoped>
.chat-sidebar {
    position: fixed;
    top: 0;
    right: 0;
    width: 380px;
    height: 100vh;
    background: var(--bg-card);
    border-left: 1px solid var(--border-color);
    box-shadow: -4px 0 12px rgba(0, 0, 0, 0.3);
    display: flex;
    flex-direction: column;
    transform: translateX(100%);
    transition: transform 0.3s ease;
    z-index: 10000;
}

.chat-sidebar.open {
    transform: translateX(0);
}

.chat-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    border-bottom: 1px solid var(--border-color);
    font-weight: 600;
    color: var(--text-primary);
}

.close-btn {
    background: none;
    border: none;
    font-size: 24px;
    cursor: pointer;
    color: var(--text-secondary);
}

.close-btn:hover {
    color: var(--text-primary);
}

.chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 16px 20px;
}

.message {
    display: flex;
    gap: 10px;
    margin-bottom: 12px;
}

.message .avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: var(--bg-secondary);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    flex-shrink: 0;
}

.message .content {
    background: var(--bg-secondary);
    padding: 8px 12px;
    border-radius: 8px;
    max-width: 80%;
    word-wrap: break-word;
    color: var(--text-primary);
}

.message.user .content {
    background: var(--accent-blue);
    color: #fff;
}

.message.assistant .content {
    background: var(--bg-hover);
}

.typing {
    opacity: 0.6;
}

.chat-input {
    display: flex;
    padding: 12px 20px;
    border-top: 1px solid var(--border-color);
    gap: 8px;
}

.chat-input input {
    flex: 1;
    padding: 8px 12px;
    background: var(--bg-input);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    outline: none;
}

.chat-input input:focus {
    border-color: var(--accent-blue);
}

.chat-input button {
    padding: 8px 16px;
    background: var(--accent-blue);
    color: #fff;
    border: none;
    border-radius: 6px;
    cursor: pointer;
}

.chat-input button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

@media (max-width: 768px) {
    .chat-sidebar {
        width: 100%;
    }

    .chat-header {
        padding: 12px 16px;
    }

    .chat-messages {
        padding: 12px;
    }

    .message .content {
        max-width: 82%;
        font-size: 14px;
    }

    .chat-input {
        padding: 10px 12px;
    }
}
</style>