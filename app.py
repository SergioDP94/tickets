import streamlit as st
import pandas as pd
import plotly.express as px

# ---------------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Analítico de Tickets",
    page_icon="📊",
    layout="wide"
)

# ---------------------------------------------------------
# CARGA Y PREPROCESAMIENTO DE DATOS
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def cargar_datos():
    url_respuestas = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTNUAuiTD8wmxJ1XKj6Pxf6aI-ZYh_40Ok4GDKg5NvBVVgr43LrDrg4TSqVnm2WXhD4JEb3HNMq3uk9/pub?gid=63689495&single=true&output=csv"
    url_responsables = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTNUAuiTD8wmxJ1XKj6Pxf6aI-ZYh_40Ok4GDKg5NvBVVgr43LrDrg4TSqVnm2WXhD4JEb3HNMq3uk9/pub?gid=1304424228&single=true&output=csv"

    df_respuestas = pd.read_csv(url_respuestas)
    df_responsables = pd.read_csv(url_responsables)

    # Conversión de fecha
    df_respuestas['Marca temporal'] = pd.to_datetime(
        df_respuestas['Marca temporal'], 
        format='%d/%m/%Y %H:%M:%S',
        errors='coerce'
    )
    
    # Columna auxiliar solo con fecha (sin hora) para agrupaciones temporales
    df_respuestas['Fecha'] = df_respuestas['Marca temporal'].dt.date

    cambio = {
        'Dirección de correo electrónico': 'correo_user',
        'Seleccione el tipo de solicitud': 'area'
    }
    df_respuestas.rename(columns=cambio, inplace=True)

    # Limpieza de espacios
    df_respuestas['area'] = df_respuestas['area'].astype(str).str.strip()
    df_responsables['area'] = df_responsables['area'].astype(str).str.strip()

    # Cruce
    df_merged = df_respuestas.merge(df_responsables, on='area', how='left')

    if 'Estado' not in df_merged.columns:
        df_merged['Estado'] = 'Pendiente'

    return df_merged

data = cargar_datos()

if 'df_tickets' not in st.session_state:
    st.session_state.df_tickets = data.copy()

# ---------------------------------------------------------
# BARRA LATERAL (FILTROS)
# ---------------------------------------------------------
st.sidebar.header("🔍 Filtros Generales")

# Filtro por Encargado
lista_encargados = ["Todos"] + sorted(st.session_state.df_tickets['nombre'].dropna().unique().tolist())
encargado_sel = st.sidebar.selectbox("Encargado:", lista_encargados)

# Filtro por Estado
lista_estados = ["Todos"] + sorted(st.session_state.df_tickets['Estado'].unique().tolist())
estado_sel = st.sidebar.selectbox("Estado:", lista_estados)

# Filtro por Rango de Fechas
min_fecha = st.session_state.df_tickets['Fecha'].min()
max_fecha = st.session_state.df_tickets['Fecha'].max()

rango_fechas = st.sidebar.date_input(
    "Rango de Fechas:",
    value=(min_fecha, max_fecha),
    min_value=min_fecha,
    max_value=max_fecha
)

if st.sidebar.button("🔄 Recargar datos"):
    st.cache_data.clear()
    st.session_state.df_tickets = cargar_datos()
    st.rerun()

# ---------------------------------------------------------
# APLICACIÓN DE FILTROS
# ---------------------------------------------------------
df_filtrado = st.session_state.df_tickets.copy()

if encargado_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado['nombre'] == encargado_sel]

if estado_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado['Estado'] == estado_sel]

if len(rango_fechas) == 2:
    f_inicio, f_fin = rango_fechas
    df_filtrado = df_filtrado[(df_filtrado['Fecha'] >= f_inicio) & (df_filtrado['Fecha'] <= f_fin)]

# ---------------------------------------------------------
# DASHBOARD SUPERIOR: KPIs Y GRÁFICAS VISUALES
# ---------------------------------------------------------
st.title("📈 Dashboard Analítico & Seguimiento de Tickets")
st.markdown(f"Vista actual para: **{encargado_sel}**")

# KPIs
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Tickets", len(df_filtrado))
col2.metric("Pendientes ⏳", len(df_filtrado[df_filtrado['Estado'] == 'Pendiente']))
col3.metric("En Proceso ⚙️", len(df_filtrado[df_filtrado['Estado'] == 'En Proceso']))
col4.metric("Resueltos ✅", len(df_filtrado[df_filtrado['Estado'] == 'Resuelto']))

st.divider()

if df_filtrado.empty:
    st.warning("No hay datos disponibles para los filtros seleccionados.")
else:
    # ---------------------------------------------------------
    # SECCIÓN DE GRÁFICAS CON PLOTLY
    # ---------------------------------------------------------
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("📅 Evolución Temporal de Tickets")
        # Agrupación por fecha para serie temporal
        df_temporal = df_filtrado.groupby(['Fecha', 'Estado']).size().reset_index(name='Cantidad')
        
        fig_linea = px.line(
            df_temporal, 
            x='Fecha', 
            y='Cantidad', 
            color='Estado',
            markers=True,
            title="Volumen Diario de Tickets por Estado",
            color_discrete_map={'Pendiente': '#EF553B', 'En Proceso': '#FECB52', 'Resuelto': '#00CC96'}
        )
        fig_linea.update_layout(xaxis_title="Fecha", yaxis_title="Cantidad de Tickets", hovermode="x unified")
        st.plotly_chart(fig_linea, use_container_width=True)

    with col_chart2:
        st.subheader("📊 Distribución por Área y Estado")
        # Gráfica de barras apiladas
        df_area = df_filtrado.groupby(['area', 'Estado']).size().reset_index(name='Cantidad')
        
        fig_barras = px.bar(
            df_area, 
            x='area', 
            y='Cantidad', 
            color='Estado',
            title="Tickets por Área de Solicitud",
            barmode='stack',
            color_discrete_map={'Pendiente': '#EF553B', 'En Proceso': '#FECB52', 'Resuelto': '#00CC96'}
        )
        fig_barras.update_layout(xaxis_title="Área", yaxis_title="Cantidad de Tickets")
        st.plotly_chart(fig_barras, use_container_width=True)

    st.divider()

    # ---------------------------------------------------------
    # SECCIÓN DE GESTIÓN Y DETALLE DE TICKETS
    # ---------------------------------------------------------
    st.subheader("📋 Gestión de Tickets")

    for idx, row in df_filtrado.iterrows():
        fecha_str = row['Marca temporal'].strftime('%d/%m/%Y %H:%M') if pd.notnull(row['Marca temporal']) else "Sin fecha"
        header_text = f"[{fecha_str}] - {row['area']} | Usuario: {row['correo_user']} | Estado: {row['Estado']}"
        
        with st.expander(header_text):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.write(f"**Fecha y Hora:** {fecha_str}")
                st.write(f"**Solicitante:** {row['correo_user']}")
                st.write(f"**Área:** {row['area']}")
                st.info(f"**Detalle:** {row['Detalle']}")
            with c2:
                st.write(f"**Encargado:** {row['nombre']}")
                nuevo_estado = st.selectbox(
                    "Cambiar Estado:",
                    options=["Pendiente", "En Proceso", "Resuelto"],
                    index=["Pendiente", "En Proceso", "Resuelto"].index(row['Estado']),
                    key=f"est_{idx}"
                )
                if nuevo_estado != row['Estado']:
                    st.session_state.df_tickets.at[idx, 'Estado'] = nuevo_estado
                    st.success("Estado actualizado")
                    st.rerun()

    # Exportación
    st.divider()
    csv = df_filtrado.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Exportar datos filtrados en CSV",
        data=csv,
        file_name="tickets_filtrados.csv",
        mime="text/csv"
    )