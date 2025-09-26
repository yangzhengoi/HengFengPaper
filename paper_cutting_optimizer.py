# paper_cutting_optimizer.py - 在线部署优化版
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import random
from itertools import product
from collections import defaultdict, Counter

# 设置页面配置
st.set_page_config(
    page_title="辊纸套切优化系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 辊纸套切优化系统")
st.markdown("""
本系统用于优化辊纸生产过程中的套切方案，通过智能算法计算最优排产计划，
最大限度提高原材料利用率，减少浪费。
""")

class PaperCuttingOptimizer:
    def __init__(self, master_width=5480, min_utilization=0.9):
        self.master_width = master_width
        self.min_utilization = min_utilization
        self.min_width = master_width * min_utilization
    
    def generate_patterns(self, widths, max_pieces=4):
        patterns = []
        
        for num_pieces in range(1, max_pieces + 1):
            for combo in product(widths, repeat=num_pieces):
                total_width = sum(combo)
                
                if total_width <= self.master_width and total_width >= self.min_width:
                    pattern_counter = Counter(combo)
                    pattern_desc = '+'.join(f"{count}×{width}" for width, count in pattern_counter.items())
                    
                    utilization = total_width / self.master_width
                    
                    patterns.append({
                        'description': pattern_desc,
                        'total_width': total_width,
                        'utilization': round(utilization, 4),
                        'composition': dict(pattern_counter),
                        'waste': self.master_width - total_width
                    })
        
        unique_patterns = {}
        for pattern in patterns:
            key = tuple(sorted(pattern['composition'].items()))
            if key not in unique_patterns or pattern['utilization'] > unique_patterns[key]['utilization']:
                unique_patterns[key] = pattern
        
        return sorted(unique_patterns.values(), key=lambda x: x['utilization'], reverse=True)
    
    def greedy_optimize(self, orders, max_iterations=1000):
        start_time = time.time()
        
        widths = list(orders.keys())
        patterns = self.generate_patterns(widths)
        patterns.sort(key=lambda x: x['utilization'], reverse=True)
        
        remaining_orders = orders.copy()
        production_plan = []
        total_coils_used = 0
        total_waste = 0
        
        iteration = 0
        while any(remaining_orders.values()) and iteration < max_iterations:
            iteration += 1
            best_pattern = None
            best_score = -1
            
            for pattern in patterns:
                feasible = True
                for width, count in pattern['composition'].items():
                    if remaining_orders.get(width, 0) < count:
                        feasible = False
                        break
                
                if feasible:
                    score = pattern['utilization']
                    for width, count in pattern['composition'].items():
                        if remaining_orders[width] == count:
                            score += 0.1
                    
                    if score > best_score:
                        best_score = score
                        best_pattern = pattern
            
            if best_pattern is None:
                for pattern in patterns:
                    max_runs = float('inf')
                    for width, count in pattern['composition'].items():
                        if count > 0:
                            max_runs = min(max_runs, remaining_orders.get(width, 0) // count)
                    
                    if max_runs > 0:
                        score = pattern['utilization'] + max_runs * 0.01
                        if score > best_score:
                            best_score = score
                            best_pattern = pattern
                            break
                
                if best_pattern is None:
                    break
            
            runs = float('inf')
            for width, count in best_pattern['composition'].items():
                if count > 0:
                    runs = min(runs, remaining_orders.get(width, 0) // count)
            
            if runs == 0:
                runs = 1
            
            production_plan.append({
                'pattern': best_pattern['description'],
                'runs': runs,
                'utilization': best_pattern['utilization'],
                'waste_per_coil': best_pattern['waste'],
                'composition': best_pattern['composition']
            })
            
            for width, count in best_pattern['composition'].items():
                remaining_orders[width] = remaining_orders.get(width, 0) - count * runs
            
            total_coils_used += runs
            total_waste += best_pattern['waste'] * runs
            
            remaining_orders = {k: v for k, v in remaining_orders.items() if v > 0}
        
        utilization_rate = 1 - (total_waste / (total_coils_used * self.master_width)) if total_coils_used > 0 else 0
        
        return {
            'method': '贪心算法',
            'production_plan': production_plan,
            'total_coils': total_coils_used,
            'total_waste': total_waste,
            'utilization_rate': round(utilization_rate, 4),
            'remaining_orders': remaining_orders,
            'computation_time': round(time.time() - start_time, 2)
        }

def main():
    # 侧边栏 - 参数设置
    st.sidebar.header("参数设置")
    
    master_width = st.sidebar.number_input("母卷宽度 (mm)", min_value=1000, max_value=10000, value=5480)
    min_utilization = st.sidebar.slider("最低利用率阈值", min_value=0.7, max_value=0.99, value=0.9)
    
    # 订单输入
    st.header("订单输入")
    
    col1, col2 = st.columns(2)
    
    with col1:
        order_input = st.text_area(
            "订单数据",
            height=200,
            value="1810,51\n1715,86\n1860,26",
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
    
    # 解析订单数据
    orders = {}
    try:
        for line in order_input.strip().split('\n'):
            if line.strip():
                width, quantity = line.strip().split(',')
                orders[int(width)] = int(quantity)
    except:
        st.error("订单数据格式错误，请检查输入格式！")
        st.stop()
    
    if not orders:
        st.warning("请输入订单数据")
        st.stop()
    
    # 显示订单摘要
    st.subheader("订单摘要")
    order_df = pd.DataFrame([(w, q) for w, q in orders.items()], columns=['宽度(mm)', '数量'])
    st.dataframe(order_df, use_container_width=True)
    
    # 初始化优化器
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
        
        # 生产计划表
        if result['production_plan']:
            st.subheader("生产计划详情")
            plan_df = pd.DataFrame(result['production_plan'])
            plan_df['总废料'] = plan_df['waste_per_coil'] * plan_df['runs']
            plan_df['利用率'] = plan_df['utilization'].apply(lambda x: f"{x*100:.2f}%")
            
            display_cols = ['pattern', 'runs', '利用率', 'waste_per_coil', '总废料']
            st.dataframe(plan_df[display_cols], use_container_width=True)
            
            # 创建可视化图表
            fig = make_subplots(
                rows=1, cols=2,
                subplot_titles=('各方案利用率', '废料分布'),
                specs=[[{"type": "bar"}, {"type": "pie"}]]
            )
            
            fig.add_trace(
                go.Bar(name='利用率', x=plan_df['pattern'], y=plan_df['utilization'].str.rstrip('%').astype('float'), 
                      marker_color='lightgreen'),
                row=1, col=1
            )
            
            fig.add_trace(
                go.Pie(labels=plan_df['pattern'], values=plan_df['总废料'], name='废料分布'),
                row=1, col=2
            )
            
            fig.update_layout(height=400, title_text="生产计划分析")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("无生产计划数据")
        
        # 剩余订单
        if result['remaining_orders']:
            st.warning(f"剩余订单: {result['remaining_orders']}")
        else:
            st.success("所有订单已完成！")
        
        # 经济效益估算
        st.subheader("经济效益估算")
        waste_saving = result['total_waste'] / 1000  # 转换为米
        cost_saving = waste_saving * 0.033 * 1.5 * 6000 / 1000  # 简化计算
        
        st.info(f"""
        - 预计节约原料: **{waste_saving:.1f} 米**
        - 预计节约成本: **{cost_saving:.0f} 元** (按33g/㎡, 1.5米幅宽, 6000元/吨估算)
        - 平均利用率: **{result['utilization_rate']*100:.1f}%**
        """)

if __name__ == "__main__":
    main()