/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import {
    Component,
    onWillStart,
    onMounted,
    onWillUnmount,
    useRef,
    useState,
} from "@odoo/owl";

// Chart.js empaquetado en Odoo (mismo que usa la vista graph). Sin libs externas.
const CHARTJS_PATH = "/web/static/lib/Chart/Chart.js";

const WINE = "#7A2E52";
const TEAL = "#1F9E8F";

/**
 * Tablero de Inicio de BCA Seguros.
 *
 * Solo dibuja: toda cifra llega ya calculada de bca.dashboard.get_dashboard_data()
 * (contrato spec §6). La navegación delega en action_open(), que devuelve el
 * act_window filtrado por dominio desde el backend (DEC-026 / D-12).
 */
export class BcaDashboard extends Component {
    static template = "BCA_Seguros.Dashboard";
    static props = {
        "*": true,
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ data: null, loading: true });

        this.charts = [];
        this.refs = {
            cartera: useRef("chart_cartera"),
            cobranza: useRef("chart_cobranza"),
            pca: useRef("chart_pca"),
            agentes: useRef("chart_agentes"),
        };

        onWillStart(async () => {
            const [data] = await Promise.all([
                this.orm.call("bca.dashboard", "get_dashboard_data", []),
                loadJS(CHARTJS_PATH),
            ]);
            this.state.data = data;
            this.state.loading = false;
        });

        onMounted(() => this._renderCharts());
        onWillUnmount(() => this._destroyCharts());
    }

    /** Abre la vista lista filtrada para la cifra clickeada. */
    async open(key) {
        const action = await this.orm.call("bca.dashboard", "action_open", [key]);
        this.action.doAction(action);
    }

    // ----------------------------------------------------------- gráficas
    _renderCharts() {
        const Chart = window.Chart;
        if (!Chart || !this.state.data) {
            return;
        }
        const d = this.state.data;
        const noAxes = { scales: { x: { display: false }, y: { display: false } } };
        const base = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
        };

        // Cartera — reparto por ramo (barras).
        this._make(this.refs.cartera, {
            type: "bar",
            data: {
                labels: ["Vida", "GMM", "Autos"],
                datasets: [{
                    data: [d.cartera.por_ramo.vida, d.cartera.por_ramo.gmm, d.cartera.por_ramo.autos],
                    backgroundColor: WINE,
                    borderRadius: 4,
                }],
            },
            options: { ...base, scales: { y: { beginAtZero: true } } },
        });

        // Cobranza — tendencia semanal (línea), última semana destacada.
        this._make(this.refs.cobranza, {
            type: "line",
            data: {
                labels: d.cobranza.tendencia_semanal.map((_, i) => `S-${5 - i}`),
                datasets: [{
                    data: d.cobranza.tendencia_semanal,
                    borderColor: TEAL,
                    backgroundColor: "rgba(31,158,143,0.12)",
                    fill: true,
                    tension: 0.3,
                    pointRadius: 2,
                }],
            },
            options: { ...base, ...noAxes },
        });

        // PCA — tendencia mensual (línea).
        this._make(this.refs.pca, {
            type: "line",
            data: {
                labels: ["E", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"],
                datasets: [{
                    data: d.pca.tendencia_mensual,
                    borderColor: WINE,
                    backgroundColor: "rgba(122,46,82,0.10)",
                    fill: true,
                    tension: 0.3,
                    pointRadius: 2,
                }],
            },
            options: { ...base, scales: { y: { display: false } } },
        });

        // Agentes — PCA por promotoría (barras).
        const prom = d.agentes.pca_por_promotoria;
        if (prom.length) {
            this._make(this.refs.agentes, {
                type: "bar",
                data: {
                    labels: prom.map((p) => p.promotoria),
                    datasets: [{
                        data: prom.map((p) => p.pca),
                        backgroundColor: TEAL,
                        borderRadius: 4,
                    }],
                },
                options: { ...base, indexAxis: "y", scales: { x: { beginAtZero: true } } },
            });
        }
    }

    _make(ref, config) {
        if (ref.el) {
            this.charts.push(new window.Chart(ref.el, config));
        }
    }

    _destroyCharts() {
        this.charts.forEach((c) => c.destroy());
        this.charts = [];
    }

    // ----------------------------------------------------------- formateo
    money(value) {
        return new Intl.NumberFormat("es-MX", {
            style: "currency",
            currency: "MXN",
            maximumFractionDigits: 0,
        }).format(value || 0);
    }

    int(value) {
        return new Intl.NumberFormat("es-MX").format(value || 0);
    }

    date(value) {
        if (!value) {
            return "—";
        }
        // Backend entrega "YYYY-MM-DD" o "YYYY-MM-DD HH:MM:SS".
        return value.slice(0, 10);
    }
}

registry.category("actions").add("bca_dashboard", BcaDashboard);
