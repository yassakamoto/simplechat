#提出時のバージョン
#FastAPIとLamda.pyの、エンドポイントのデータ形式を合わせるのがミソだった。
#FastAPI側は、単なる文字列をPOST/generateでJSON形式送っている形だったので、受け取り側のLamda.pyもエンドポイントの形をそろえる必要あり
#　凹　⇔　凸　みたいな感じ。
#FastAPIの公開URLは起動ごとに変わるので注意。
import json
import os
import urllib.request
import urllib.error

# FastAPIの公開URL
FASTAPI_URL = os.environ.get("FASTAPI_URL", "https://3f3c-34-16-161-110.ngrok-free.app/generate")

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))

        # Lambda呼び出し時のリクエストボディを解析
        body = json.loads(event['body'])
        message = body.get('message')
        if not message:
            raise ValueError("Missing 'message' in request body")

        # FastAPI が期待するリクエスト形式を構築
        request_payload = {
            "prompt": message,
            "max_new_tokens": 512,
            "temperature": 0.7,
            "top_p": 0.9,
            "do_sample": True
        }

        print("Sending to FastAPI:", json.dumps(request_payload))

        req = urllib.request.Request(
            url=FASTAPI_URL,
            data=json.dumps(request_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        # FastAPI へリクエスト送信
        with urllib.request.urlopen(req, timeout=30) as res:
            response_body = json.loads(res.read().decode("utf-8"))

        print("FastAPI response:", json.dumps(response_body))

        if "generated_text" not in response_body:
            raise Exception("No 'generated_text' in response")

        assistant_response = response_body["generated_text"]

        # 成功レスポンスを返す
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response
            })
        }

    except urllib.error.HTTPError as e:
        error_message = e.read().decode()
        print("HTTPError:", e.code, error_message)
        return {
            "statusCode": e.code,
            "body": json.dumps({"success": False, "error": f"HTTPError {e.code}: {error_message}"})
        }

    except Exception as error:
        print("Error:", str(error))
        return {
            "statusCode": 500,
            "body": json.dumps({"success": False, "error": str(error)})
        }


"""
# lambda/index.py
import json
import os
import boto3
import re  # 正規表現モジュールをインポート
from botocore.exceptions import ClientError
import urllib.request # ✅ 追加
import urllib.error # ✅ 追加


# Lambda コンテキストからリージョンを抽出する関数
##def extract_region_from_arn(arn):
    # ARN 形式: arn:aws:lambda:region:account-id:function:function-name
##    match = re.search('arn:aws:lambda:([^:]+):', arn)
##    if match:
##        return match.group(1)
##    return "us-east-1"  # デフォルト値

# グローバル変数としてクライアントを初期化（初期値）
# ✅bedrock_client = None

# モデルID
# ✅MODEL_ID = os.environ.get("MODEL_ID", "us.amazon.nova-lite-v1:0")

# ✅ FastAPIのエンドポイント（環境変数にしておくと後で変更しやすい）
FASTAPI_URL = os.environ.get("FASTAPI_URL", "https://c51b-34-125-20-78.ngrok-free.app/generate")

def lambda_handler(event, context):
    try:
        # コンテキストから実行リージョンを取得し、クライアントを初期化
        ##global bedrock_client
        ##if bedrock_client is None:
        ##    region = extract_region_from_arn(context.invoked_function_arn)
        ##    bedrock_client = boto3.client('bedrock-runtime', region_name=region)
        ##    print(f"Initialized Bedrock client in region: {region}")
        
        print("Received event:", json.dumps(event))
        
        # Cognitoで認証されたユーザー情報を取得
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")
        
        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])
        
        print("Processing message:", message)
        ##print("Using model:", MODEL_ID)
        
        # 会話履歴を使用
        messages = conversation_history.copy()
        
        # ユーザーメッセージを追加
        messages.append({
            "role": "user",
            "content": message
        })
        
        # Nova Liteモデル用のリクエストペイロードを構築
        # 会話履歴を含める
        bedrock_messages = []
        for msg in messages:
            if msg["role"] == "user":
                bedrock_messages.append({
                    "role": "user",
                    "content": [{"text": msg["content"]}]
                })
            elif msg["role"] == "assistant":
                bedrock_messages.append({
                    "role": "assistant", 
                    "content": [{"text": msg["content"]}]
                })
        
        # invoke_model用のリクエストペイロード
        request_payload = {
            "messages": bedrock_messages,
            "inferenceConfig": {
                "maxTokens": 512,
                "stopSequences": [],
                "temperature": 0.7,
                "topP": 0.9
            }
        }
        
        print("Calling FastAPI (i/o Bedrock invoke_model API) with payload:", json.dumps(request_payload))
        
        # invoke_model APIを呼び出し・・・の代わりに、FastAPI呼出しに変更
        ##response = bedrock_client.invoke_model(
        ##    modelId=MODEL_ID,
        ##    body=json.dumps(request_payload),
        ##    contentType="application/json"
        ##)
        ##if response.status_code != 200:
        ##    raise Exception(f"LLM API error: {response.status_code} - {response.text}")      
        # レスポンスを解析
        ##response_body = json.loads(response['body'].read())
        ##print("Bedrock response:", json.dumps(response_body, default=str))

        ## urllib.request を使った POST リクエスト
        req = urllib.request.Request(
            url=FASTAPI_URL,
            data=json.dumps(request_payload).encode('utf-8'),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=30) as res:
            response_body = json.loads(res.read().decode("utf-8"))

        print("FastAPI response:", json.dumps(response_body, default=str))
              
        
        # 応答の検証
        if not response_body.get('output') or not response_body['output'].get('message') or not response_body['output']['message'].get('content'):
            raise Exception("No response content from the model")
        
        # アシスタントの応答を取得
        ##assistant_response = response_body['output']['message']['content'][0]['text']
        assistant_response = response_body.get('response') or "(no response)"
        
        # アシスタントの応答を会話履歴に追加
        messages.append({
            "role": "assistant",
            "content": assistant_response
        })
        
        # 成功レスポンスの返却
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": messages
            })
        }
        
    except Exception as error:
        print("Error:", str(error))
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }
"""
