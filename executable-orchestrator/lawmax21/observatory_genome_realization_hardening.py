"""Bind exact candidate identity into genome-realization auditor prompts.

The original overlay validated ``report.candidate_id`` but its free-form task did not expose the
candidate ID as a dedicated context block. Depending on ticket metadata that is not part of the model
prompt would make a correct response impossible or invite inference from unrelated artefacts. This
wrapper adds the identity mechanically before either independent auditor is called.
"""
from types import MethodType


def install(ctx, handlers):
    if getattr(ctx, "_genome_realization_prompt_hardened", False):
        return dict(handlers)
    original = ctx.ask

    def ask(self, role, ticket, task, context_blocks, schema,
            line="main", temperature=0.0):
        blocks = list(context_blocks)
        if str(role).startswith("genome-realization-auditor-"):
            candidate_id = str(ticket).rsplit("::", 1)[-1]
            blocks = [("CANDIDATE ID", candidate_id)] + blocks
        return original(role, ticket, task, blocks, schema,
                        line=line, temperature=temperature)

    ctx.ask = MethodType(ask, ctx)
    ctx._genome_realization_prompt_hardened = True
    return dict(handlers)
