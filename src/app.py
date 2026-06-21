import streamlit as st
import simpy
import random
import pandas as pd
import plotly.express as px
import math
from datetime import datetime
import os
import time

st.set_page_config(page_title="Simulador M/M/s", layout="wide")

st.title("Simulador M/M/s")
st.markdown("**Investigación Operativa** | Por: LEONARDO ALVARO JORGE OROSCO")

st.sidebar.header("📊 Parámetros de la Simulación")

lambda_rate = st.sidebar.number_input("λ - Tasa de llegada (por hora)", min_value=1.0, value=30.0, step=0.5)
mu_rate = st.sidebar.number_input("μ - Tasa de servicio por servidor (por hora)", min_value=1.0, value=18.0, step=0.5)
num_servers = st.sidebar.number_input("s - Número de servidores", min_value=1, max_value=10, value=2)
simulation_hours = st.sidebar.number_input("Horas de simulación", min_value=1, max_value=24, value=8)


if st.sidebar.button("🚀 Ejecutar Simulación", type="primary", use_container_width=True):
    with st.spinner("Ejecutando simulación con animación..."):
        
        status_container = st.empty()
        queue_container = st.empty()
        progress_bar = st.progress(0)
        
        env = simpy.Environment()
        resource = simpy.Resource(env, capacity=num_servers)
        
        arrivals, waits, services, totals = [], [], [], []
        
        def entity(env, name):
            arrival = env.now
            arrivals.append(arrival)
            with resource.request() as req:
                yield req
                wait = env.now - arrival
                waits.append(wait)
                service = random.expovariate(mu_rate)
                services.append(service)
                yield env.timeout(service)
                totals.append(env.now - arrival)
        
        def generator(env):
            i = 0
            while env.now < simulation_hours:
                yield env.timeout(random.expovariate(lambda_rate))
                i += 1
                env.process(entity(env, f'C{i}'))
        
        env.process(generator(env))
        
        # Animación
        step = 0.5
        current_time = 0.0
        while current_time < simulation_hours:
            current_time += step
            env.run(until=current_time)
            current_queue = resource.count
            current_waiting = len(resource.queue)
            
            status_container.info(f"⏱️ Hora simulada: **{current_time:.1f}** | Servidores ocupados: **{current_queue}/{num_servers}** | En cola: **{current_waiting}**")
            servers_status = "🟢 " * (num_servers - current_queue) + "🔴 " * current_queue
            queue_container.markdown(f"**Estado de Servidores:** {servers_status} &nbsp;&nbsp; **Esperando:** {current_waiting} personas")
            
            progress_bar.progress(min(current_time / simulation_hours, 1.0))
            time.sleep(0.25)
        
        # Resultados
        min_len = min(len(arrivals), len(waits), len(services), len(totals))
        df = pd.DataFrame({
            'Cliente': [f'C{i+1}' for i in range(min_len)],
            'Tiempo_Espera_min': [w*60 for w in waits[:min_len]],
            'Tiempo_Servicio_min': [s*60 for s in services[:min_len]],
            'Tiempo_Total_min': [t*60 for t in totals[:min_len]]
        })
        
        rho = lambda_rate / (num_servers * mu_rate)
        a = lambda_rate / mu_rate
        sum_term = sum((a**n) / math.factorial(n) for n in range(num_servers))
        last_term = (a**num_servers / math.factorial(num_servers)) * (1 / (1 - rho)) if rho < 1 else 0
        p0 = 1 / (sum_term + last_term) if rho < 1 else 0
        pq = ((a**num_servers / math.factorial(num_servers)) * (1 / (1 - rho)) * p0) if rho < 1 else 0
        lq = pq * (rho / (1 - rho)) if rho < 1 else 0
        l = lq + a
        wq = lq / lambda_rate if lambda_rate > 0 else 0
        w = wq + 1/mu_rate
        
        sim_wq_min = df['Tiempo_Espera_min'].mean()
        sim_lq = lambda_rate * (sim_wq_min / 60)

        # Guardar en session_state para que no se pierda
        st.session_state.df = df
        st.session_state.rho = rho
        st.session_state.p0 = p0
        st.session_state.pq = pq
        st.session_state.lq = lq
        st.session_state.l = l
        st.session_state.wq = wq
        st.session_state.w = w
        st.session_state.sim_wq_min = sim_wq_min
        st.session_state.sim_lq = sim_lq
        st.session_state.num_servers = num_servers
        st.session_state.lambda_rate = lambda_rate
        st.session_state.mu_rate = mu_rate
        
        st.success(f"✅ Simulación completada con {len(df)} entidades")


if 'df' in st.session_state:
    tab2, tab4, tab5 = st.tabs([
        "📐 Medidas Teóricas M/M/s", 
        "🔍 Interpretación", 
        "💰 Análisis Económico"
    ])

    
    with tab2:
        st.subheader("📐 Medidas de Desempeño Teóricas M/M/s")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("ρ **(Fracción del tiempo que cada servidor está ocupado)**", f"{st.session_state.rho:.4f} ({st.session_state.rho*100:.2f}%)")
            st.metric("P₀ **(probabilidad de sistema vacío)**", f"{st.session_state.p0:.4f} ({st.session_state.p0*100:.2f}%)")
            st.metric("Pq **(Prob. de que un cliente tenga que hacer cola)**", f"{st.session_state.pq:.4f} ({st.session_state.pq*100:.2f}%)")
        with col2:
            st.metric("Lq **(Número promedio esperando en cola)**", f"{st.session_state.lq:.4f}")
            st.metric("L **(Número promedio esperando en el sistema)**", f"{st.session_state.l:.4f}")
            st.metric("Wq **(Tiempo promedio en cola)**", f"{st.session_state.wq:.4f} horas / {st.session_state.wq*60:.2f} minutos")  
            st.metric("W **(Tiempo promedio en el sistema)**", f"{st.session_state.w:.4f} horas / {st.session_state.w*60:.2f} minutos")
    
    with tab4:
            st.subheader("🔍 Interpretación de los Resultados")
            
            
            st.write(f"### 1. Factor de utilización ρ -> ({st.session_state.rho*100:.2f}%)")
            if st.session_state.rho >= 1.0:
                st.error("**Sistema saturado / inestable** — La demanda supera la capacidad")
            elif st.session_state.rho >= 0.85:
                st.warning("**Sistema al límite** — Muy cargado")
            elif st.session_state.rho >= 0.70:
                st.info("**Sistema cargado pero estable** - El sistema funciona bien")
            elif st.session_state.rho >= 0.50:
                st.success("**Utilización saludable** - El sistema tiene un balance adecuado")
            else:
                st.success("**Sistema subutilizado** - Los servidores están ociosos buena parte del tiempo")
            
            
            st.write(f"### 2. Probabilidad de sistema vacío (P₀) -> ({st.session_state.p0*100:.2f}%)")
            if st.session_state.p0 < 0.05:
                st.info("Demanda constante. El sistema casi nunca está vacío.")
            elif st.session_state.p0 > 0.30:
                st.success("Alta capacidad ociosa.")
            else:
                st.info("Equilibrio razonable entre actividad y descanso de servidores")
            
            
            st.write(f"### 3. Probabilidad de esperar (Pq) -> ({st.session_state.pq*100:.2f}%)")
            if st.session_state.pq > 0.80:
                st.error("**Crítico** — Más del 80% de los clientes esperan.")
            elif st.session_state.pq > 0.50:
                st.warning("**Señal de alerta** - Más de la mitad de las personas deberán esperar")
            elif st.session_state.pq > 0.20:
                st.info("Nivel aceptable - Una proporción relevante espera, pero no es alarmante")
            else:
                st.success("**Buen nivel de servicio** - La gran mayoría es atendida de inmediato")
            
            
            st.write(f"### 4. Número promedio en cola (Lq) -> ({st.session_state.lq:.4f})")
            if st.session_state.lq < 1:
                st.success("Cola prácticamente inexistente.")
            elif st.session_state.lq <= 3:
                st.info("Cola corta y manejable.")
            elif st.session_state.lq <= 6:
                st.warning("Cola moderada; empieza a notarse.")
            else:
                st.error("Cola larga; riesgo de incomodidad.")


            st.write(f"### 5. Número promedio en el sistema (L) -> ({st.session_state.l:.4f})")
            if st.session_state.l < num_servers:
                st.success("El lugar luce despejado. Hay holgura.")
                st.success("En promedio el local está cómodo: hay menos personas que servidores disponibles.")
            elif st.session_state.l <= num_servers * 1.5:
                st.info("Ocupación normal y bien dimensionada.")
                st.info("El número de personas en el sistema coincide con la cantidad de servidores, lo cual es saludable.")
            elif st.session_state.l < num_servers * 2:
                st.warning("Hay cola estructural. Se nota la acumulación.")
                st.warning("En promedio hay más personas que servidores, lo que confirma que se está formando cola de manera habitual.")
            else:
                st.error("Acumulación alta. Revisar espacio físico y capacidad.")
                st.error("La acumulación promedio es considerablemente mayor a la capacidad de servidores; conviene revisar si el espacio físico es suficiente.")
            
            
            st.write(f"### 6. Tiempo de espera promedio (Wq) -> ({st.session_state.wq:.4f} horas / {st.session_state.wq*60:.2f} min)")
            st.success("⚠️ Aquí el umbral **SÍ** depende del contexto del sistema")

            
            
            st.write(f"### 7. Tiempo total en el sistema (W) -> ({st.session_state.w:.4f} horas / {st.session_state.w*60:.2f} min)")
            st.success("⚠️ Aquí el umbral **SÍ** depende del contexto del sistema")

    with tab5:
        st.subheader("💰 Análisis Económico")
        st.write("Ingresa los costos para comparar si conviene agregar un servidor más.")
        
        cs = st.number_input("Costo de un servidor por hora (S/.)", min_value=0.0, value=15.0, step=0.5)
        cw = st.number_input("Costo de espera del cliente por hora (S/.)", min_value=0.0, value=25.0, step=0.5)
        
        costo_actual = (st.session_state.num_servers * cs) + (st.session_state.lq * cw)
        
        rho_new = st.session_state.lambda_rate / ((st.session_state.num_servers + 1) * st.session_state.mu_rate)
        if rho_new < 1:
            a_new = st.session_state.lambda_rate / st.session_state.mu_rate
            sum_term_new = sum((a_new**n) / math.factorial(n) for n in range(st.session_state.num_servers + 1))
            last_term_new = (a_new**(st.session_state.num_servers+1) / math.factorial(st.session_state.num_servers+1)) * (1 / (1 - rho_new))
            p0_new = 1 / (sum_term_new + last_term_new)
            pq_new = (a_new**(st.session_state.num_servers+1) / math.factorial(st.session_state.num_servers+1)) * (1 / (1 - rho_new)) * p0_new
            lq_new = pq_new * (rho_new / (1 - rho_new))
        else:
            lq_new = 999
        
        costo_nuevo = ((st.session_state.num_servers + 1) * cs) + (lq_new * cw)
        ahorro = costo_actual - costo_nuevo
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Costo Total Actual", f"S/. {costo_actual:.2f}")
        with col2:
            st.metric(f"Costo con {st.session_state.num_servers+1} servidores", f"S/. {costo_nuevo:.2f}", 
                     delta=f"S/. {ahorro:.2f}" if ahorro > 0 else f"S/. {ahorro:.2f}")
        
        if ahorro > 0:
            st.success(f"✅ **Conviene agregar 1 servidor**. Ahorro estimado: **S/. {ahorro:.2f} por hora**.")
        else:
            st.warning("❌ No conviene económicamente agregar un servidor más.")