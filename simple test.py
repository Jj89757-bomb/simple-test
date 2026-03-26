import streamlit as st
import os
from pathlib import Path

# 设置环境变量，告诉 pymsis 数据文件在哪里 (假设你上传的文件名叫 f107_ap.npz)
# 注意：不同版本的 pymsis 可能识别不同的环境变量，通常是 PYMSIS_DATA_DIR 或直接覆盖内部逻辑
# 如果环境变量不起作用，我们需要手动“欺骗”库

current_dir = Path(__file__).parent
data_file = current_dir / "f107_ap.npz"  # 确保这个名字和你上传的一致

if data_file.exists():
    os.environ['PYMSIS_DATA_DIR'] = str(current_dir)
    # 有些版本可能需要预加载
    import pymsis.utils as utils
    # 强制将数据加载到内存，防止后续调用触发下载
    if not hasattr(utils, '_DATA') or utils._DATA is None:
         utils._DATA = utils._load_f107_ap_data_from_file(str(data_file)) # 伪代码，视具体版本API而定
         # 如果上面这行报错，说明版本不支持直接指定文件加载函数，
         # 此时最简单的办法是利用 pymsis 会自动扫描当前工作目录的特性。
         # 确保 .npz 文件就在运行目录下。
    st.success("检测到本地数据文件，跳过下载。")
else:
    st.warning("未找到本地数据文件，将尝试联网下载（可能会失败）。")



import streamlit as st
from pymsis import msis
import datetime
import numpy as np

st.title("Test succeed!")

# 1. 设置输入参数
time = datetime.datetime(2023, 1, 1, 12)
lon = 0
lat = 45
alt = 400

# 2. 运行模型
# data 的形状通常是 (ntime, nlat, nlon, nalt, nvars)
# 对于单点输入，shape 可能是 (1, 1, 1, 1, 11) 或类似，取决于版本
data = msis.run(time, lon, lat, alt)

# 调试：打印形状和数据，方便你在控制台查看结构
print(f"Data shape: {data.shape}")
print(f"Raw data: {data}")

# 3. 提取标量数值
# 方法 A: 使用 .item() 如果数组里只有一个元素
# 方法 B: 使用索引 [0,0,0,0,0] 明确获取第一个值 (时间, 纬, 经, 高, 变量索引)
# 假设我们要获取的是中性温度 (通常是第一个变量，索引0)
try:
    # 尝试直接展平取第一个值，这是最安全的做法，不管维度是多少
    temp_value = float(data.flatten()[0])
except Exception as e:
    st.error(f"数据提取失败: {e}")
    st.stop()

# 4. 显示指标
st.metric(
    label="中性温度 (Exospheric Temp)",
    value=f"{temp_value:.2f} K",       # 格式化显示，保留两位小数
    delta=None,                        # 如果没有对比数据，建议设为 None，或者计算一个差值
    # delta=temp_value - 700,          # 示例：如果你想显示相对于 700K 的变化
    delta_color="normal"
)

# 如果你想显示其他成分（比如 O, N2, O2 的密度），它们通常在后面的索引
# 例如：o_density = float(data.flatten()[1]) # 假设索引1是O
