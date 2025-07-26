import sys
import io
from functools import wraps
from PyQt6.QtWidgets import QApplication, QMainWindow, QListView, QPushButton, QVBoxLayout, QWidget
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import QObject, pyqtSignal

class OutputCollector(QObject):
    """输出收集器，使用信号槽机制安全更新UI"""
    new_output = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.log_model = QStandardItemModel()
        # 连接信号到槽函数
        self.new_output.connect(self.add_to_list)
    
    def add_to_list(self, text):
        """将输出添加到列表模型"""
        item = QStandardItem(text)
        self.log_model.appendRow(item)

# 创建输出收集器实例
output_collector = OutputCollector()

def collect_output(func):
    """装饰器：捕获函数中的print输出，并添加到listView中"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 保存原始的stdout
        original_stdout = sys.stdout
        # 创建一个StringIO对象用于捕获输出
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        try:
            # 执行被装饰的函数
            result = func(*args, **kwargs)
            # 获取捕获的输出并按行分割
            output = captured_output.getvalue().strip()
            if output:
                # 按行发送输出内容，避免一次性发送过多内容
                for line in output.split('\n'):
                    if line.strip():
                        output_collector.new_output.emit(line.strip())
            return result
        finally:
            # 恢复原始的stdout
            sys.stdout = original_stdout
    return wrapper

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Collect Output Example")
        self.setGeometry(100, 100, 400, 300)
        
        # 创建布局和控件
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        
        # 初始化listView并关联模型
        self.listView = QListView()
        self.listView.setModel(output_collector.log_model)
        
        # 创建测试按钮
        self.test_button = QPushButton("运行测试函数")
        self.test_button.clicked.connect(self.test_function)
        
        # 创建清空按钮
        self.clear_button = QPushButton("清空列表")
        self.clear_button.clicked.connect(self.clear_list)
        
        # 添加控件到布局
        layout.addWidget(self.listView)
        layout.addWidget(self.test_button)
        layout.addWidget(self.clear_button)
        
        self.setCentralWidget(central_widget)
    
    @collect_output
    def test_function(self,*args):
        """测试函数，包含print输出"""
        print("测试函数开始执行")
        print("这是一条测试信息")
        print("函数执行完毕")
        # 测试多行输出
        print("\n多行输出示例：")
        print("第一行")
        print("第二行")
    
    def clear_list(self):
        """清空listView内容"""
        output_collector.log_model.clear()
        print("列表已清空")  # 这条print也会被捕获

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
    
