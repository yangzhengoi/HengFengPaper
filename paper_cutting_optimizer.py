# paper_cutting_optimizer.py - 添加恒丰纸业Logo版本
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from itertools import product
from collections import Counter
import time
import base64

# 设置页面配置 - 同时设置标签页图标和页面标题
st.set_page_config(
    page_title="恒丰纸业 - 辊纸套切优化系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式，用于美化Logo显示
def add_custom_css():
    st.markdown("""
    <style>
    .logo-container {
        text-align: center;
        margin-bottom: 20px;
    }
    .logo-img {
        max-width: 300px;
        height: auto;
    }
    .company-title {
        text-align: center;
        color: #1f77b4;
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# 显示Logo的函数
def display_logo(logo_path, width=300):
    try:
        # 方法1: 直接使用st.image
        st.image(logo_path, width=width)
    except:
        try:
            # 方法2: 使用HTML和base64编码（备用方案）
            with open(logo_path, "rb") as f:
                logo_data = base64.b64encode(f.read()).decode()
            
            st.markdown(f"""
            <div class="logo-container">
                <img src="data:image/png;base64,{logo_data}" class="logo-img" alt="恒丰纸业Logo">
            </div>
            """, unsafe_allow_html=True)
        except Exception as e:
            st.warning(f"Logo加载失败: {str(e)}")

# 主应用代码
def main():
    # 添加自定义CSS
    add_custom_css()
    
    # ==================== 页面顶部Logo和标题 ====================
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # 显示公司标题
        st.markdown('<div class="company-title">恒丰纸业</div>', unsafe_allow_html=True)
        
        # 尝试加载Logo（多种路径尝试）
        logo_paths = [
            "hengfeng_logo.png",           # 根目录
            "assets/hengfeng_logo.png",    # assets文件夹
            "images/hengfeng_logo.png",    # images文件夹
            "logo.png"                     # 通用名称
        ]
        
        logo_loaded = False
        for logo_path in logo_paths:
            try:
                display_logo(logo_path, width=250)
                logo_loaded = True
                break
            except:
                continue
        
        if not logo_loaded:
            # 如果找不到Logo文件，显示文字替代
            st.markdown("""
            <div style="text-align: center; padding: 20px; border: 2px dashed #ccc; border-radius: 10px;">
                <h3>恒丰纸业</h3>
                <p>辊纸套切优化系统</p>
            </div>
            """, unsafe_allow_html=True)
    
    # 应用主标题
    st.title("📊 辊纸套切优化系统")
    st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        本系统用于优化辊纸生产过程中的套切方案，通过智能算法计算最优排产计划，
        最大限度提高原材料利用率，减少浪费。
    </div>
    """, unsafe_allow_html=True)
    
    # ==================== 侧边栏设置 ====================
    st.sidebar.markdown("## 🏢 恒丰纸业")
    
    # 侧边栏也可以显示小尺寸Logo
    with st.sidebar:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            try:
                st.image("hengfeng_logo.png", width=100)
            except:
                st.markdown("**恒丰纸业**")
    
    st.sidebar.header("参数设置")
    
    master_width = st.sidebar.number_input("母卷宽度 (mm)", min_value=1000, max_value=10000, value=5480)
    min_utilization = st.sidebar.slider("最低利用率阈值", min_value=0.7, max_value=0.99, value=0.9)
    
    # ==================== 订单输入部分 ====================
    st.header("📋 订单输入")
    
    # 添加示例选择
    example_option = st.selectbox(
        "选择示例数据或手动输入",
        ["手动输入", "示例1: 1810×51, 1715×86, 1860×26", "示例2: 1510×37, 1720×10, 1900×49"]
    )
    
    if example_option == "示例1: 1810×51, 1715×86, 1860×26":
        default_orders = "1810,51\n1715,86\n1860,26"
    elif example_option == "示例2: 1510×37, 1720×10, 1900×49":
        default_orders = "1510,37\n1720,10\n1900,49"
    else:
        default_orders = ""
    
    col1, col2 = st.columns(2)
    
    with col1:
        order_input = st.text_area(
            "订单数据",
            height=200,
            value=default_orders,
            help="每行输入一个规格，格式：宽度(mm),数量"
        )
    
    with col2:
        st.markdown("""
        **输入示例：**
        ```
        1810,51
        1715,86
        1860,26
        ```
        
        **说明：**
        - 每行一个规格
        - 格式：宽度(mm),数量
        - 宽度为整数，数量为整数
        """)
    
    # ==================== 订单处理逻辑（保持不变）====================
    # 解析订单数据
    orders = {}
    try:
        for line in order_input.strip().split('\n'):
            if line.strip():
                width, quantity = line.strip().split(',')
                width_val = int(width)
                quantity_val = int(quantity)
                
                if width_val > master_width:
                    st.error(f"错误：规格宽度 {width_val}mm 超过母卷宽度 {master_width}mm，无法生产！")
                    st.stop()
                
                orders[width_val] = quantity_val
    except Exception as e:
        st.error(f"订单数据格式错误，请检查输入格式！错误: {str(e)}")
        st.stop()
    
    if not orders:
        st.warning("请输入订单数据")
        st.stop()
    
    # 显示订单摘要
    st.subheader("订单摘要")
    order_df = pd.DataFrame([(w, q) for w, q in orders.items()], columns=['宽度(mm)', '数量'])
    st.dataframe(order_df, use_container_width=True)
    
    # 优化器类和优化逻辑保持不变...
    # 这里省略了PaperCuttingOptimizer类的定义以保持简洁
    # 您需要将之前完整的PaperCuttingOptimizer类定义放在这里
    
    # 初始化优化器
    from paper_cutting_optimizer_class import PaperCuttingOptimizer  # 假设类在单独文件中
    # 或者直接在这里定义PaperCuttingOptimizer类
    
    optimizer = PaperCuttingOptimizer(master_width, min_utilization)
    
    # 生成可行方案
    with st.spinner("正在生成可行切割方案..."):
        patterns = optimizer.generate_patterns(list(orders.keys()))
    
    st.subheader("可行切割方案")
    st.write(f"共生成 {len(patterns)} 个可行方案")
    
    # 显示部分高效方案
    if patterns:
        top_patterns = patterns[:10]
        pattern_data = []
        for p in top_patterns:
            pattern_data.append({
                '方案': p['description'],
                '总宽度(mm)': p['total_width'],
                '利用率': f"{p['utilization']*100:.2f}%",
                '废料(mm)': p['waste']
            })
        
        patterns_df = pd.DataFrame(pattern_data)
        st.dataframe(patterns_df, use_container_width=True)
    else:
        st.error("未找到可行切割方案，请调整参数或订单数据！")
        st.stop()
    
    # 运行优化算法
    st.header("优化计算")
    
    if st.button("开始优化计算", type="primary"):
        with st.spinner("正在计算最优方案..."):
            result = optimizer.greedy_optimize(orders.copy())
        
        # 显示结果
        st.header("优化结果")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("总生产车数", result['total_coils'])
        col2.metric("原料利用率", f"{result['utilization_rate']*100:.2f}%")
        col3.metric("总废料(mm·车)", result['total_waste'])
        col4.metric("计算时间(秒)", result['computation_time'])
        
        # 检查是否完全消耗了订单
        if result['remaining_orders']:
            st.error(f"⚠️ 未能完全消耗所有订单，剩余: {result['remaining_orders']}")
        else:
            st.success("✅ 所有订单已完全消耗！")
        
        # 生产计划表
        if result['production_plan']:
            st.subheader("生产计划详情")
            plan_df = pd.DataFrame(result['production_plan'])
            plan_df['总废料'] = plan_df['waste_per_coil'] * plan_df['runs']
            plan_df['利用率百分比'] = plan_df['utilization'].apply(lambda x: f"{x*100:.2f}%")
            
            display_cols = ['pattern', 'runs', '利用率百分比', 'waste_per_coil', '总废料']
            st.dataframe(plan_df[display_cols], use_container_width=True)
            
            # 添加下载功能
            csv = plan_df[display_cols].to_csv(index=False)
            st.download_button(
                label="下载生产计划CSV",
                data=csv,
                file_name="恒丰纸业_生产计划.csv",
                mime="text/csv"
            )
        
        # 页脚添加公司信息
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #666; font-size: 14px;">
            <p>恒丰纸业有限公司 - 辊纸套切优化系统</p>
            <p>© 2024 恒丰纸业 版权所有</p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
