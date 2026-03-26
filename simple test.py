import streamlit as st
import os
import shutil
from pathlib import Path
import datetime
import numpy as np
import re

# ================= 配置 =================
DATA_FILE_NAME = "f107_ap.npz"
# =======================================

st.set_page_config(page_title="NRLMSIS Data Injection", page_icon="💉")
st.title("💉 NRLMSIS-2.0 数据注入版")

# 1. 准备并加载数据文件
current_dir = Path(__file__).parent.resolve()
source_path = current_dir / DATA_FILE_NAME

if not source_path.exists():
    st.error(f"❌ 找不到 {DATA_FILE_NAME}")
    st.stop()

try:
    raw_data = np.load(str(source_path), allow_pickle=True)
    # 转换为 pymsis 期望的字典格式
    # 确保日期是 datetime64 类型
    dates = raw_data['dates'].astype('datetime64')
    f107 = raw_data['f107'].astype(float)
    ap = raw_data['ap'].astype(float)
    
    INJECTED_DATA = {
        "dates": dates,
        "f107": f107,
        "ap": ap
    }
    st.success(f"✅ 数据已加载并格式化：{len(dates)} 条记录")
except Exception as e:
    st.error(f"数据处理失败: {e}")
    st.stop()

# 2. 【核心大招】直接注入全局变量 _DATA
# 必须在导入 pymsis.msis 之前或之后立即执行，确保 _DATA 不为 None
import pymsis.utils

# 直接赋值！这样 pymsis 认为数据已经加载好了，绝不会尝试联网或下载
pymsis.utils._DATA = INJECTED_DATA

# 为了防止它尝试重新加载，我们也覆盖加载函数为空
pymsis.utils._load_f107_ap_data = lambda: INJECTED_DATA
pymsis.utils.download_f107_ap = lambda: None

st.info("💉 数据注入成功！pymsis 将直接使用内存中的数据，禁止联网。")

# 3. 运行计算
st.divider()
st.subheader("🚀 开始计算")

time_val = datetime.datetime(2023, 1, 1, 12, 0, 0)
lon_val = 0.0
lat_val = 45.0
alt_val = 400.0

# 这里的数值其实不重要，因为 _DATA 已经被注入了，
# 但如果 options 传对了，它会优先用 options。
# 为了触发使用 _DATA 的逻辑，我们可以故意传 None 或者错误的 options？
# 不，还是传正确的 options 格式，如果它能用最好，不能用它会 fallback 到 _DATA。
base_option = {
    'f107': 150.0, 
    'f107a': 150.0, 
    'ap': 4.0, 
    'ap_prev': 4.0
}

def run_msis_with_auto_retry(t, l, la, a, base_opt):
    from pymsis import msis
    
    current_options = [base_opt]
    
    try:
        output = msis.run([t], [l], [la], [a], options=current_options)
        return output, 1
    except ValueError as e:
        error_msg = str(e)
        if "needs to be a list of length" in error_msg:
            match = re.search(r"length (\d+)", error_msg)
            if match:
                needed_len = int(match.group(1))
                st.write(f"⚙️ 检测到输入被广播为 {needed_len} 个点，正在自动适配...")
                
                current_options = [base_opt] * needed_len
                
                # 重试
                output = msis.run([t], [l], [la], [a], options=current_options)
                return output, needed_len
        raise e

with st.spinner("正在计算大气参数..."):
    try:
        output, final_len = run_msis_with_auto_retry(time_val, lon_val, lat_val, alt_val, base_option)
        
        st.success(f"✅ 计算成功！(内部处理了 {final_len} 个数据点)")
        
        # 解析结果
        if output.ndim == 2:
            first_point = output[0]
        else:
            reshaped = output.reshape(-1, 11)
            first_point = reshaped[0]
            
        temp = float(first_point[0])
        density = float(first_point[1])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="中性温度 (Temperature)", value=f"{temp:.2f} K")
        with col2:
            st.metric(label="总质量密度 (Density)", value=f"{density:.2e} kg/m³")
            
        st.balloons()
        st.success("💉 完美！数据注入成功，无网络请求！")
        
        with st.expander("查看完整输出数据"):
            st.write(f"输出形状: {output.shape}")
            st.dataframe(output.reshape(-1, 11)[:5])

    except Exception as e:
        st.error(f"💥 发生错误: {e}")
        import traceback
        st.code(traceback.format_exc())
