import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Dashboard de Tickets por Encargado",
    page_icon="🎫",
    layout="wide"
)

# ---------------------------------------------------------
# CARGA Y PREPROCESAMIENTO DE DATOS
# ---------------------------------------------------------
@st.cache_data(ttl=60)  # Recarga datos cada 60 segundos
def cargar_datos():
    # URLs de Google Sheets (CSV)
    url_respuestas = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTNUAuiTD8wmxJ1XKj6Pxf6aI-ZYh_40Ok4GDKg5NvBVVgr43LrDrg4TSqVnm2WXhD4JEb3HNMq3uk9/pub?gid=63689495&single=true&output=csv"
    url_responsables = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTNUAuiTD8wmxJ1XKj6Pxf6aI-ZYh_40Ok4GDKg5NvBVVgr43LrDrg4TSqVnm2WXhD4JEb3HNMq3uk9/pub?gid=1304424228&single=true&output=csv"

    # Lectura
    df_respuestas = pd.read_csv(url_respuestas)
    df_responsables = pd.read_csv(url_responsables)

    # Transformación de datos
    df_respuestas['Marca temporal'] = pd.to_datetime(
        df_respuestas['Marca temporal'], 
        format='%d/%m/%Y %H:%M:%S',
        errors='coerce'
    )
    
    cambio = {
        'Dirección de correo electrónico': 'correo_user',
        'Seleccione el tipo de solicitud': 'area'
    }
    df_respuestas.rename(columns=cambio, inplace=True)

    # Limpieza de espacios en texto
    df_respuestas['area'] = df_respuestas['area'].astype(str).str.strip()
    df_responsables['area'] = df_responsables['area'].astype(str).str.strip()

    # Cruce (merge) de información
    df_merged = df_respuestas.merge(df_responsables, on='area', how='left')

    # Se asume un estado inicial para el seguimiento si no viene desde origen
    if 'Estado' not in df_merged.columns:
        df_merged['Estado'] = 'Pendiente'

    return df_merged

# Cargar DataFrame en memoria
data = cargar_datos()

# Estado de sesión (para mantener modificaciones locales de estados)
if 'df_tickets' not in st.session_state:
    st.session_state.df_tickets = data.copy()

# ---------------------------------------------------------
# BARRA LATERAL (FILTROS)
# ---------------------------------------------------------
st.sidebar.header("🔍 Filtros de Seguimiento")

# Selector de Encargado/Responsable
lista_encargados = ["Todos"] + sorted(st.session_state.df_tickets['nombre'].dropna().unique().tolist())
encargado_sel = st.sidebar.selectbox("Selecciona tu nombre (Encargado):", lista_encargados)

# Selector de Estado del Ticket
lista_estados = ["Todos"] + sorted(st.session_state.df_tickets['Estado'].unique().tolist())
estado_sel = st.sidebar.selectbox("Filtrar por Estado:", lista_estados)

# Botón para refrescar la carga de datos
if st.sidebar.button("🔄 Recargar datos de Google Sheets"):
    st.cache_data.clear()
    st.session_state.df_tickets = cargar_datos()
    st.rerun()

# ---------------------------------------------------------
# APLICACIÓN DE FILTROS AL DATAFRAME
# ---------------------------------------------------------
df_filtrado = st.session_state.df_tickets.copy()

if encargado_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado['nombre'] == encargado_sel]

if estado_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado['Estado'] == estado_sel]

# ---------------------------------------------------------
# ENCABEZADO Y MÉTRICAS CLAVE (KPIs)
# ---------------------------------------------------------
st.title("🎫 Dashboard de Gestión y Seguimiento de Tickets")
st.markdown(f"Mostrando información asignada a: **{encargado_sel}**")

col1, col2, col3, col4 = st.columns(4)

total_tickets = len(df_filtrado)
pendientes = len(df_filtrado[df_filtrado['Estado'] == 'Pendiente'])
en_proceso = len(df_filtrado[df_filtrado['Estado'] == 'En Proceso'])
resueltos = len(df_filtrado[df_filtrado['Estado'] == 'Resuelto'])

col1.metric("Total Tickets", total_tickets)
col2.metric("Pendientes ⏳", pendientes)
col3.metric("En Proceso ⚙️", en_proceso)
col4.metric("Resueltos ✅", resueltos)

st.divider()

# ---------------------------------------------------------
# VISTA INTERACTIVA DE TICKETS
# ---------------------------------------------------------
st.subheader("📋 Lista de Tickets Asignados")

if df_filtrado.empty:
    st.info("No hay tickets que coincidan con los filtros seleccionados.")
else:
    # Renderizar cada ticket en un contenedor expandible
    for idx, row in df_filtrado.iterrows():
        header_text = f"Ticket del {row['Marca temporal'].strftime('%d/%m/%Y %H:%M')} | {row['area']} | Usuario: {row['correo_user']} [{row['Estado']}]"
        
        with st.expander(header_text):
            col_det1, col_det2 = st.columns([3, 1])

            with col_det1:
                st.write(f"**Área solicitada:** {row['area']}")
                st.write(f"**Usuario solicitante:** {row['correo_user']}")
                st.write(f"**Detalle de la solicitud:**")
                st.info(row['Detalle'])

            with col_det2:
                st.write(f"**Responsable:** {row['nombre']}")
                st.write(f"**Contacto:** {row['correo']}")
                
                # Permite cambiar el estado directamente desde la interfaz
                nuevo_estado = st.selectbox(
                    "Actualizar Estado:",
                    options=["Pendiente", "En Proceso", "Resuelto"],
                    index=["Pendiente", "En Proceso", "Resuelto"].index(row['Estado']),
                    key=f"estado_{idx}"
                )

                # Si cambia el estado, se actualiza el estado global de la sesión
                if nuevo_estado != row['Estado']:
                    st.session_state.df_tickets.at[idx, 'Estado'] = nuevo_estado
                    st.success(f"Estado actualizado a '{nuevo_estado}'")
                    st.rerun()

# ---------------------------------------------------------
# VISTA GLOBAL EN TABLA Y EXPORTACIÓN
# ---------------------------------------------------------
st.divider()
st.subheader("📊 Resumen General de Datos")

st.dataframe(
    df_filtrado[['Marca temporal', 'correo_user', 'area', 'nombre', 'Estado', 'Detalle']],
    use_container_width=True
)

# Exportar datos filtrados a CSV
csv = df_filtrado.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Descargar vista actual en CSV",
    data=csv,
    file_name="seguimiento_tickets.csv",
    mime="text/csv"
)