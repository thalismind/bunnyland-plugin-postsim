"""Optional, lazily imported 3D appearance for postal entities."""

from .components import MailboxComponent


def install_postsim_3d(actor, context) -> None:
    if context.plugins is None or not context.plugins.enabled("bunnyland.3d"):
        return
    from bunnyland_3d import (
        EntityVisualContribution,
        EntityVisualRule,
        ModelAsset,
        ModelTransform,
        PrimitivePart3D,
        ProceduralModelSource,
        VisualMaterial3D,
        register_entity_visuals,
        register_models,
    )

    owner = "bunnyland.postsim"
    model_key = f"{owner}/mailbox"
    register_models(
        actor,
        owner,
        (
            ModelAsset(
                key=model_key,
                source=ProceduralModelSource(
                    parts=(
                        PrimitivePart3D(
                            "box",
                            "box",
                            size=(0.8, 0.8, 0.55),
                            transform=ModelTransform(translation=(0, 0.75, 0)),
                            material=VisualMaterial3D(color="#356b91", metallic=0.5),
                            roles=("damageable", "lock-anchor", "state-indicator"),
                        ),
                        PrimitivePart3D(
                            "lid",
                            "box",
                            size=(0.84, 0.08, 0.6),
                            transform=ModelTransform(translation=(0, 1.19, -0.22)),
                            material=VisualMaterial3D(color="#477ea5", metallic=0.5),
                            roles=("openable",),
                        ),
                        PrimitivePart3D(
                            "post",
                            "cylinder",
                            radius=0.09,
                            height=0.7,
                            transform=ModelTransform(translation=(0, 0.35, 0)),
                            material=VisualMaterial3D(color="#6c4a32"),
                        ),
                    ),
                    required_roles=("openable", "lock-anchor"),
                ),
            ),
        ),
    )
    register_entity_visuals(
        actor,
        owner,
        (
            EntityVisualRule(
                key=f"{owner}/mailbox",
                predicate=lambda entity: entity.has_component(MailboxComponent),
                contribution=EntityVisualContribution(base_model_key=model_key),
            ),
        ),
    )


__all__ = ["install_postsim_3d"]
