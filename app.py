import os
import uuid
from flask import Flask, request, jsonify, render_template, send_from_directory, url_for
from http import HTTPStatus
from urllib.parse import urlparse, unquote
from pathlib import PurePosixPath
import requests
from dashscope import ImageSynthesis
import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/generated'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制上传大小为16MB

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    """主页面路由，返回前端HTML"""
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_image():
    """生成动漫人物的API端点"""
    try:
        # 获取前端发送的JSON数据
        data = request.get_json()
        
        # 获取三个关键词，如果没有提供则使用默认值
        keyword1 = data.get('keyword1', '金发').strip()
        keyword2 = data.get('keyword2', '碧眼').strip()
        keyword3 = data.get('keyword3', '女仆装').strip()
        
        # 构建完整的提示词
        prompt = f"动漫风格人物无背景全身照，特征：{keyword1}，{keyword2}，{keyword3}"
        
        # 记录请求日志
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] 生成请求 - 关键词: {keyword1}, {keyword2}, {keyword3}")
        print(f"[{timestamp}] 提示词: {prompt}")
        
        # 获取API密钥
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'API密钥未配置，请设置DASHSCOPE_API_KEY环境变量'
            }), 500
        
        # 调用DashScope API生成图像
        print('----sync call, please wait a moment----')
        rsp = ImageSynthesis.call(
            api_key=api_key,
            model="wanx2.1-t2i-turbo",
            prompt=prompt,
            n=1,
            size='1024*1024'
        )
        print('response: %s' % rsp)
        
        # 检查API响应状态
        if rsp.status_code == HTTPStatus.OK:
            # 生成唯一的文件名
            file_name = f"{uuid.uuid4().hex}.png"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
            
            # 保存图片
            for result in rsp.output.results:
                # 获取图片URL
                image_url = result.url
                
                # 下载图片
                response = requests.get(image_url)
                if response.status_code == 200:
                    with open(save_path, 'wb') as f:
                        f.write(response.content)
                        print("当前工作目录:", os.getcwd())
                        print("保存图片绝对路径:", os.path.abspath(save_path))
                    
                    # 记录成功日志
                    print(f"[{timestamp}] 图像生成成功: {save_path}")
                    
                    # 获取完整的图片URL
                    image_full_url = url_for('generated_image', filename=file_name, _external=True)
                    print(f"[{timestamp}] 完整图片URL: {image_full_url}")
                    
                    return jsonify({
                        'success': True, 
                        'image_url': image_full_url,  # 使用完整的URL
                        'prompt': prompt
                    })
                else:
                    return jsonify({
                        'success': False, 
                        'error': f'图片下载失败: HTTP {response.status_code}'
                    }), 500
            
            return jsonify({
                'success': False, 
                'error': '未获取到生成结果'
            }), 500
        else:
            # API调用失败处理
            error_msg = f'API调用失败: 状态码={rsp.status_code}, 错误代码={rsp.code}, 消息={rsp.message}'
            print(f"[{timestamp}] {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500
            
    except Exception as e:
        # 异常处理
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'服务器内部错误: {str(e)}'
        }), 500

@app.route('/test-image')
def test_image():
    return send_from_directory('static/generated', '测试图片.png')

@app.route('/static/generated/<filename>')
def generated_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    # 检查API密钥是否设置
    if not os.getenv("DASHSCOPE_API_KEY"):
        print("警告: DASHSCOPE_API_KEY环境变量未设置!")
    
    # 启动Flask应用
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
