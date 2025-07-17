import json
from datetime import datetime
# Our official coze sdk for Python [cozepy](https://github.com/coze-dev/coze-py)
from cozepy import COZE_CN_BASE_URL
from pydantic import BaseModel

# Get an access_token through personal access token or oauth.
coze_api_token = 'sat_cPsWh2jkHtikAqqkEdFb7zJHO12siDaHnqjFGbUwJBG9StsFcbil8klznTSTjpTh'
# The default access is api.coze.com, but if you need to access api.coze.cn,
# please use base_url to configure the api endpoint to access
coze_api_base = COZE_CN_BASE_URL

from cozepy import Coze, TokenAuth, Message, ChatStatus, MessageContentType  # noqa

class FeishuUser(BaseModel):
    id: str
    name: str
    email: str
    en_name: str

class ContactRecord(BaseModel):
    user: FeishuUser
    follow_user: list[FeishuUser]

class WorkState(BaseModel):
    table_id: str
    table_name: str
    records: dict

class RecordBase(BaseModel):
    owner: list[str]

class MonthlyTargetRecord(RecordBase):
    target: str
    month: str

class WeeklyTargetRecord(RecordBase):
    target: str
    week: str
    state: str
    progress: str
    parent: str

class TaskRecord(RecordBase):
    name: str
    state: str
    estimate_time: float
    progress: float
    parent: str


class OwnerTaskData(BaseModel):
    owner: FeishuUser
    task_list: list[TaskRecord]
    monthly_target: list[MonthlyTargetRecord]
    weekly_target: list[WeeklyTargetRecord]

class WorkStateAnalyzer:
    def __init__(self):
        self.coze = Coze(auth=TokenAuth(token=coze_api_token), base_url=coze_api_base)
        self.workflow_id = '7527887328314376227'
        self.record_map = {}
        self.owner_task_data_map = {}

    def run(self):
        work_states = self.get_work_state()
        self.build_record_map(work_states)
        self.build_owner_task_data()
        print(self.to_markdown())

    def get_work_state(self) -> list[WorkState]:
        try:
            workflow = self.coze.workflows.runs.create(
                workflow_id=self.workflow_id,
            )

            output_json = json.loads(workflow.data)
            return [WorkState(**item) for item in output_json.get("output", {})]
        except Exception as e:
            print(e)
            return {}
        
    def build_record_map(self, work_states: list[WorkState]):
        for work_state in work_states:
            table_name = work_state.table_name
            print(f"表格名：{table_name}")
            if table_name in ["团队通讯录", "00_月度目标", "01_周目标", "02_任务列表", "03_问题记录表"]:
                print(f"√ 处理表格：{table_name}")
                items = work_state.records.get("items", [])
                for item in items:
                    record_id = item.get("record_id", "")
                    fields = item.get("fields", {})
                    fields_json = json.loads(fields)
                    self.record_map[record_id] = fields_json

                    if table_name == "00_月度目标":
                        monthly_target_record = to_monthly_target_record(fields_json)
                        self.record_map[record_id] = monthly_target_record
                    elif table_name == "01_周目标":
                        weekly_target_record = to_weekly_target_record(fields_json)
                        self.record_map[record_id] = weekly_target_record
                    elif table_name == "02_任务列表":
                        task_record = to_task_record(fields_json)
                        self.record_map[record_id] = task_record
                    elif table_name == "03_问题记录表":
                        pass
                    elif table_name == "团队通讯录":
                        contact_record = to_contact_record(fields_json)
                        self.record_map[record_id] = contact_record
                    else:
                        print(f"× 跳过表格：{table_name}")
                        continue
            else:
                print(f"× 跳过表格：{table_name}")
                continue
            print("-"*100)
        return self.record_map
    
    def build_owner_task_data(self):
        for record_id, record in self.record_map.items():
            if isinstance(record, RecordBase):
                owner = self.record_map.get(record.owner[0], None)
                if owner and isinstance(owner, ContactRecord):
                    if owner.user.name not in self.owner_task_data_map:
                        self.owner_task_data_map[owner.user.name] = OwnerTaskData(
                            owner=owner.user,
                            task_list=[],
                            monthly_target=[],
                            weekly_target=[],
                        )
                    
                    owner_task_data = self.owner_task_data_map[owner.user.name]
                    if isinstance(record, TaskRecord):
                        owner_task_data.task_list.append(record)
                    elif isinstance(record, MonthlyTargetRecord):
                        owner_task_data.monthly_target.append(record)
                    elif isinstance(record, WeeklyTargetRecord):
                        owner_task_data.weekly_target.append(record)

    def to_markdown(self):
        markdown = ""
        for owner, owner_task_data in self.owner_task_data_map.items():
            # print(owner_task_data)
            markdown += f"## {owner} 的工作日报 - {datetime.now().strftime('%Y-%m-%d')}\n\n"
            markdown += self._get_monthly_target_markdown(owner_task_data)
            markdown += self._get_weekly_target_markdown(owner_task_data)
            markdown += self._get_task_list_markdown(owner_task_data)
        return markdown
    
    def _get_weekly_target_markdown(self, owner_task_data: OwnerTaskData) -> str:
        markdown = ""
        markdown += f"### 周目标\n\n"
        if owner_task_data.weekly_target:
            headers = [field for field in owner_task_data.weekly_target[0].model_dump().keys()]
            markdown += "| " + " | ".join(headers) + " |\n"
            markdown += "| " + " | ".join(["---"] * len(headers)) + " |\n"
            for weekly_target in owner_task_data.weekly_target:
                values = [self._get_attribute_value(weekly_target, field) for field in headers]
                markdown += "| " + " | ".join(values) + " |\n"
        markdown += "\n\n"
        return markdown
    
    def _get_task_list_markdown(self, owner_task_data: OwnerTaskData) -> str:
        markdown = ""
        markdown += f"### 每周任务列表\n\n"
        if owner_task_data.task_list:
            headers = [field for field in owner_task_data.task_list[0].model_dump().keys()]
            markdown += "| " + " | ".join(headers) + " |\n"
            markdown += "| " + " | ".join(["---"] * len(headers)) + " |\n"
            for task_record in owner_task_data.task_list:
                values = [self._get_attribute_value(task_record, field) for field in headers]
                markdown += "| " + " | ".join(values) + " |\n"
        markdown += "\n"
        return markdown
    
    def _get_monthly_target_markdown(self, owner_task_data: OwnerTaskData) -> str:
        markdown = ""
        markdown += f"### 月度目标\n\n"
        # 输出表头
        if owner_task_data.monthly_target:
            headers = [field for field in owner_task_data.monthly_target[0].model_dump().keys()]
            markdown += "| " + " | ".join(headers) + " |\n"
            markdown += "| " + " | ".join(["---"] * len(headers)) + " |\n"
            # 输出每一行
            for monthly_target in owner_task_data.monthly_target:
                values = [self._get_attribute_value(monthly_target, field) for field in headers]
                markdown += "| " + " | ".join(values) + " |\n"
        else:
            markdown += "无月度目标\n\n"
        markdown += "\n\n"
        return markdown
    
    def _get_attribute_value(self, record: RecordBase, field: str) -> str:
        if record.model_dump().get(field, None):
            attr = record.model_dump().get(field, "")
            if field in ["owner", "parent"]:
                first_attr = attr[0] if isinstance(attr, list) else attr
                object = self.record_map.get(first_attr, {})
                # print(f"{attr} : {first_attr} : {object}")


                if isinstance(object, FeishuUser):
                    return object.name
                elif isinstance(object, ContactRecord):
                    return object.user.name
                elif isinstance(object, TaskRecord):
                    return object.name
                elif isinstance(object, MonthlyTargetRecord):
                    return object.target
                elif isinstance(object, WeeklyTargetRecord):
                    return object.target
                else:
                    return str(object.model_dump().get("name", ""))
            else:
                return str(attr)
        else:
            return ""

def to_monthly_target_record(fields: dict) -> MonthlyTargetRecord:
    # print(fields)
    return MonthlyTargetRecord(
        target=fields.get("目标", "")[0].get("text", ""),
        month=fields.get("目标周期", ""),
        owner=fields.get("负责人", "").get('link_record_ids'),
    )

def to_weekly_target_record(fields: dict) -> WeeklyTargetRecord:
    # print(fields)
    return WeeklyTargetRecord(
        target=fields.get("目标", "")[0].get("text", ""),
        week=fields.get("年度第几周", "").get("value", [{}])[0].get("text", ""),
        owner=fields.get("负责人", "").get('link_record_ids'),
        state=fields.get("状态", "").get("value", [{}])[0].get("text", ""),
        progress=fields.get("完成度", "").get("value", [{}])[0].get("text", ""),
        parent=fields.get("00_月度目标", "").get('link_record_ids')[0],
    )

def to_task_record(fields: dict) -> TaskRecord:
    # print(fields)
    return TaskRecord(
        name=fields.get("任务名称", [{}])[0].get("text", ""),
        owner=fields.get("责任人", {}).get('link_record_ids', []),
        state=fields.get("状态", ""),
        estimate_time=fields.get("预估工期（天）", 0.0),
        progress=fields.get("实际工期", {}).get("value", [0])[0] if fields.get("实际工期", {}).get("value") else 0.0,
        parent=fields.get("周目标", "").get('link_record_ids')[0],
    )

def to_contact_record(fields: dict) -> ContactRecord:
    # 获取成员信息（第一个成员作为主要用户）
    members = fields.get("成员", [])
    user_data = members[0] if members else {}
    
    # 获取关注人列表
    follow_users_data = fields.get("关注人", [])
    
    # 构建主要用户对象
    user = FeishuUser(
        id=user_data.get("id", ""),
        name=user_data.get("name", ""),
        email=user_data.get("email", ""),
        en_name=user_data.get("en_name", "")
    )
    
    # 构建关注人列表
    follow_users = []
    for follow_user_data in follow_users_data:
        follow_user = FeishuUser(
            id=follow_user_data.get("id", ""),
            name=follow_user_data.get("name", ""),
            email=follow_user_data.get("email", ""),
            en_name=follow_user_data.get("en_name", "")
        )
        follow_users.append(follow_user)
    
    return ContactRecord(
        user=user,
        follow_user=follow_users
    )

if __name__ == "__main__":
    work_state_analyzer = WorkStateAnalyzer()
    record_map = work_state_analyzer.run()
