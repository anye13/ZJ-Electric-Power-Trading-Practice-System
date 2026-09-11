from zai import ZhipuAiClient

# 初始化客户端
client = ZhipuAiClient(api_key="470c2eecc7484ad4bba03801e50c50a5.fCxqzRVC2nFJYu9x")

# 创建聊天完成请求
response = client.chat.completions.create(
    model="glm-4-plus",
    messages=[
        {
            "role": "system",
            "content": "你是一个乐于解答各种问题的助手，你的任务是为用户提供专业、准确、有见地的建议。",
        },
        {"role": "user", "content": "你好，请介绍一下自己"},
    ],
    max_tokens=4096,
    temperature=0.7,
)

# 获取回复
print(response.choices[0].message.content)
