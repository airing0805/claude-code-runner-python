
多选对话框返回到前端的数据结构如下：                                         
  发送给后端的答案格式：                                                        
  {                                                                             
    "session_id": "session_xxx",                                                    "question_id": "选择操作",                                                      "answer": "继续当前任务"  // 用户选择的选项 label                             }                                                                                                                                                               完整的前端交互流程：                                                                                                                                            1. 后端推送问答消息 (通过 SSE)：                                              
  {
    "type": "ask_user_question",
    "question": {
      "question_id": "选择操作",
      "header": "选择操作",
      "question_text": "你想让我做什么？",
      "type": "multiple_choice",
      "options": [
        {"id": "continue", "label": "继续当前任务", "description":
  "继续当前正在进行的任务"},
        {"id": "structure", "label": "查看代码结构", "description":
  "查看项目代码结构和文件组织"},
        {"id": "create", "label": "创建新文件", "description":
  "在项目中创建一个新文件"},
        {"id": "test", "label": "运行测试", "description": "运行项目中的测试"}  
      ],
      "required": true
    }
  }

  2. 用户选择后提交答案：
  POST /api/task/answer
  {
    "session_id": "session_xxx",
    "question_id": "选择操作",
    "answer": "continue"
  }

  3. 后端响应：
  {
    "success": true,
    "message": "答案已提交，任务继续执行"
  }
