from __future__ import annotations

from odoo import fields, models


class BcaPolizaCambioAgente(models.Model):
    """M4: Historial inmutable de cambios de agente en una póliza.

    Los registros se crean exclusivamente desde bca.poliza.cambiar_agente()
    — no hay UI ni API para crearlos manualmente. Las pólizas históricas
    siguen acreditando a la promotoría original al liquidar (R-ORG-02).
    """

    _name = 'bca.poliza.cambio.agente'
    _description = 'Historial de Cambio de Agente en Póliza'
    _order = 'fecha_cambio desc, id desc'

    poliza_id: int = fields.Many2one(
        'bca.poliza',
        string='Póliza',
        required=True,
        ondelete='cascade',
        readonly=True,
        index=True,
    )
    agente_anterior_id: int = fields.Many2one(
        'res.partner',
        string='Agente Anterior',
        required=True,
        readonly=True,
        ondelete='restrict',
    )
    promotoria_anterior_id: int = fields.Many2one(
        'res.partner',
        string='Promotoría Anterior',
        readonly=True,
        ondelete='restrict',
    )
    agente_nuevo_id: int = fields.Many2one(
        'res.partner',
        string='Agente Nuevo',
        required=True,
        readonly=True,
        ondelete='restrict',
    )
    promotoria_nueva_id: int = fields.Many2one(
        'res.partner',
        string='Promotoría Nueva',
        readonly=True,
        ondelete='restrict',
    )
    fecha_cambio: fields.Date = fields.Date(
        string='Fecha del Cambio',
        required=True,
        readonly=True,
        default=fields.Date.context_today,
    )
    motivo: str = fields.Char(string='Motivo', readonly=True)
    usuario_id: int = fields.Many2one(
        'res.users',
        string='Autorizado por',
        required=True,
        readonly=True,
        default=lambda self: self.env.user,
    )
