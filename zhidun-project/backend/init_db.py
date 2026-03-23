import sqlite3
import json

scenarios_data = {
    "qinqing": {
        "name": "亲情陷阱",
        "intro": "妈，我是小明！我出车祸了，急需5万块钱救命！快给我转账！",
        "questions": [
            {"question": "接到这样的电话，您应该怎么做？", "options": ["立即转账救孩子", "先挂电话，打孩子原号码确认", "问对方银行卡号", "向亲戚借钱"], "correct": 1, "explanation": "正确！遇到亲人求助，一定要通过原号码核实，骗子最怕你打电话确认。"},
            {"question": "对方说来不及了快转账，您觉得可疑吗？", "options": ["不可疑，孩子着急", "可疑，制造紧迫感是诈骗常用手法", "不确定", "应该相信"], "correct": 1, "explanation": "对！骗子就是利用紧迫感让您来不及思考，越急越要冷静。"},
            {"question": "对方说我换号了这是新号码，可信吗？", "options": ["可信", "不可信，可能是骗子", "半信半疑", "先转一点试试"], "correct": 1, "explanation": "正确！骗子常用换号借口，真的换号会提前告知。"},
            {"question": "如果对方能说出孩子的名字和学校，就是真的吗？", "options": ["是真的", "不一定，信息可能泄露了", "肯定是真的", "应该相信"], "correct": 1, "explanation": "对！个人信息可能被泄露，骗子会利用这些信息取信。"},
            {"question": "遇到这种情况，最保险的做法是？", "options": ["先转钱再说", "视频通话确认", "问更多问题", "报警"], "correct": 1, "explanation": "正确！视频通话是最直接的确认方式，骗子无法伪装。"}
        ]
    },
    "yangsheng": {
        "name": "养生迷局",
        "intro": "阿姨您好！我是健康专家，您的体检报告显示有严重问题，需要立即购买我们的特效药，原价9800，现在只要3980！",
        "questions": [
            {"question": "陌生人说您有健康问题，您应该？", "options": ["立即购买", "去正规医院检查", "先买了试试", "问问邻居"], "correct": 1, "explanation": "正确！健康问题一定要去正规医院，不要相信陌生人的体检报告。"},
            {"question": "对方说限时优惠过期涨价，这是什么手法？", "options": ["真的优惠", "制造紧迫感诱导购买", "为我好", "不确定"], "correct": 1, "explanation": "对！这是典型的饥饿营销，骗子用限时优惠逼您快速决策。"},
            {"question": "对方自称专家，您应该怎么做？", "options": ["相信专家", "要求看资质证书", "直接购买", "不用管"], "correct": 1, "explanation": "正确！真正的专家会有正规资质，要求查看证书是您的权利。"},
            {"question": "保健品能治疗严重疾病吗？", "options": ["能", "不能，保健品不是药", "有些能", "试试看"], "correct": 1, "explanation": "对！保健品只能辅助保健，不能治病，生病要看医生。"},
            {"question": "对方说很多老人都买了，您觉得？", "options": ["那我也买", "这是从众心理陷阱", "应该不错", "可以试试"], "correct": 1, "explanation": "正确！骗子利用从众心理，别人买不代表产品好。"}
        ]
    },
    "baoxian": {
        "name": "百万保障",
        "intro": "您好，我是支付宝客服，您的账户存在异常，需要提供验证码验证身份，否则账户将被冻结！",
        "questions": [
            {"question": "对方要验证码，您应该？", "options": ["立即提供", "绝不提供，挂断电话", "先问问情况", "提供一半"], "correct": 1, "explanation": "正确！验证码就是密码，任何人要验证码都是诈骗！"},
            {"question": "真正的客服会主动要验证码吗？", "options": ["会", "不会，正规客服绝不会要", "有时会", "不清楚"], "correct": 1, "explanation": "对！正规平台客服永远不会主动索要验证码、密码等信息。"},
            {"question": "对方说账户异常要冻结，您应该？", "options": ["赶紧配合", "挂断后自己登录APP查看", "提供信息", "很害怕"], "correct": 1, "explanation": "正确！不要相信电话，自己登录官方APP查看才安全。"},
            {"question": "对方能说出您的姓名和部分卡号，就是真客服吗？", "options": ["是", "不一定，信息可能泄露", "肯定是", "应该是"], "correct": 1, "explanation": "对！个人信息泄露很常见，骗子会用这些信息取信。"},
            {"question": "如何辨别真假客服电话？", "options": ["听声音", "挂断后拨打官方客服核实", "看来电显示", "问问题"], "correct": 1, "explanation": "正确！主动拨打官方客服电话核实是最安全的方法。"}
        ]
    },
    "gongzheng": {
        "name": "公检法诈骗",
        "intro": "我是XX市公安局的，您涉嫌一起洗钱案，需要配合调查，请将资金转入安全账户！",
        "questions": [
            {"question": "公安局会通过电话办案吗？", "options": ["会", "不会，公安办案必须当面", "有时会", "不知道"], "correct": 1, "explanation": "正确！公安机关办案必须出示证件、当面询问，不会电话要求转账。"},
            {"question": "对方说有安全账户，您觉得？", "options": ["应该转", "这是诈骗术语，没有安全账户", "可以试试", "不确定"], "correct": 1, "explanation": "对！安全账户是诈骗黑话，公检法没有任何安全账户。"},
            {"question": "对方要求不能告诉任何人，这是为什么？", "options": ["保密需要", "怕您求助，方便行骗", "办案需要", "为您好"], "correct": 1, "explanation": "正确！骗子怕您跟家人商量被识破，所以要求保密。"},
            {"question": "真的涉案会怎么处理？", "options": ["电话通知", "民警上门出示证件", "发短信", "发邮件"], "correct": 1, "explanation": "对！真的涉案，民警会上门并出示证件，绝不会电话要钱。"},
            {"question": "接到这种电话应该怎么做？", "options": ["配合调查", "挂断后拨打110核实", "转账", "很害怕"], "correct": 1, "explanation": "正确！直接拨打110报警核实，不要相信陌生来电。"}
        ]
    }
}

conn = sqlite3.connect('zhidun.db')
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS questions
             (scenario_id TEXT, q_id INTEGER, background_text TEXT,
              question_text TEXT, options TEXT, correct INTEGER, explanation TEXT)''')

for scenario_id, data in scenarios_data.items():
    for q_id, q in enumerate(data['questions']):
        c.execute('INSERT INTO questions VALUES (?,?,?,?,?,?,?)',
                  (scenario_id, q_id, data['intro'], q['question'],
                   json.dumps(q['options'], ensure_ascii=False), q['correct'], q['explanation']))

conn.commit()
conn.close()
print("数据库初始化完成！")
