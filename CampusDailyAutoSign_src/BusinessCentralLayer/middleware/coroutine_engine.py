__all__ = ['CampusDailySpeedUp']

from gevent import monkey

monkey.patch_all()
import gevent
from gevent.queue import Queue

from BusinessCentralLayer.middleware.data_io import refresh_database


class CoroutineEngine(object):
    """协程加速控件"""

    def __init__(self, core, config_path=None, user_cluster=None, power: int = 8, progress_name: str = '任务进度'):
        """

        :param core: 驱动核心
        :param user_cluster:
        :param power:
        :param progress_name: 进度条
        """
        # 配置文件地址
        self.config_path = config_path

        self.max_queue_size = 0
        self.now_queue_size = 0
        self.power = power
        self.progress_name = progress_name
        self.work_Q = Queue()
        self.user_cluster = user_cluster

        # 驱动器
        self.core = core

    def load_tasks(self, tasks=None):
        if isinstance(tasks, list):
            for task in tasks:
                self.work_Q.put_nowait(task)
        elif not tasks and self.config_path:
            data: dict = refresh_database(self.config_path, purview='read')
            for key, value in data.items():
                self.work_Q.put_nowait(value)
        self.max_queue_size = self.work_Q.qsize()
        # 弹性协程
        self.power = 72 if self.max_queue_size >= 72 else self.max_queue_size

    def launch(self):
        while not self.work_Q.empty():
            task = self.work_Q.get_nowait()
            self.control_driver(task)

    # 移交外部控制权
    def control_driver(self, task):
        """
        重写此模块
        :param task:
        :return:
        """

    # 进度条
    def progress_manager(self, total, desc='Example', leave=True, ncols=100, unit='B', unit_scale=True):
        """
        进度监测
        :return:
        """
        from tqdm import tqdm
        import time
        # iterable: 可迭代的对象, 在手动更新时不需要进行设置
        # desc: 字符串, 左边进度条描述文字
        # page_size: 总的项目数
        # leave: bool值, 迭代完成后是否保留进度条
        # file: 输出指向位置, 默认是终端, 一般不需要设置
        # ncols: 调整进度条宽度, 默认是根据环境自动调节长度, 如果设置为0, 就没有进度条, 只有输出的信息
        # unit: 描述处理项目的文字

        with tqdm(total=total, desc=desc, leave=leave, ncols=ncols,
                  unit=unit, unit_scale=unit_scale) as progress_bar:
            progress_bar.update(self.power)
            while not self.work_Q.empty():
                now_1 = self.work_Q.qsize()
                time.sleep(0.1)
                now_2 = self.work_Q.qsize() - now_1
                progress_bar.update(abs(now_2))

    # 入口
    def run(self, speed_up=True):
        """
        协程任务接口
        :return:
        """
        task_list = []

        # 刷新任务队列
        self.load_tasks(tasks=self.user_cluster)

        # 启动进度条
        exec("import sys"
             "\nimport threading"
             "\nthreading.Thread(target=self.progress_manager,"
             "args=(self.max_queue_size, self.progress_name + '[{}]'.format(self.power))).start()")

        # 弹性协程
        if not speed_up:
            self.power = 1

        for x in range(self.power):
            task = gevent.spawn(self.launch)
            task_list.append(task)
        gevent.joinall(task_list)


class CampusDailySpeedUp(CoroutineEngine):
    """协程控件继承"""

    def __init__(self, core, config_path=None, power: int = 4, progress_name: str = '任务进度', task_list=None):
        super(CampusDailySpeedUp, self).__init__(core=core, power=power, user_cluster=task_list,
                                                 progress_name=progress_name, config_path=config_path)

    def control_driver(self, task):
        self.core.run(task)
