"""Enable the extensions the schema depends on.

This must be the first migration. Autogenerate does not add extension calls, so
a schema created without it will fail the moment a vector column appears.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001_enable_extensions"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
