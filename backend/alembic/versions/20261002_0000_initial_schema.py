"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-10-02 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create contracts table
    op.create_table(
        'contracts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='draft'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # Create contract_versions table
    op.create_table(
        'contract_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('contract_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=True),
        sa.Column('file_type', sa.String(50), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('parsing_metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], ondelete='CASCADE'),
    )

    # Create parties table
    op.create_table(
        'parties',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('contract_version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(100), nullable=True),
        sa.Column('source_section', sa.String(100), nullable=True),
        sa.Column('source_page', sa.Integer(), nullable=True),
        sa.Column('source_quote', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['contract_version_id'], ['contract_versions.id'], ondelete='CASCADE'),
    )

    # Create extracted_items table
    op.create_table(
        'extracted_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('contract_version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('item_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('date_value', sa.DateTime(), nullable=True),
        sa.Column('notice_period_days', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('conditions', sa.Text(), nullable=True),
        sa.Column('purpose', sa.String(100), nullable=True),
        sa.Column('automatic', sa.String(10), nullable=True),
        sa.Column('certainty', sa.String(20), nullable=False, default='medium'),
        sa.Column('source_section', sa.String(100), nullable=True),
        sa.Column('source_page', sa.Integer(), nullable=True),
        sa.Column('source_quote', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('review_status', sa.String(50), nullable=False, default='pending'),
        sa.Column('is_stale', sa.String(10), nullable=False),
        sa.Column('user_edited', sa.String(10), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['contract_version_id'], ['contract_versions.id'], ondelete='CASCADE'),
    )

    # Create obligations table
    op.create_table(
        'obligations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('contract_version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('responsible_party', sa.String(255), nullable=True),
        sa.Column('deadline', sa.DateTime(), nullable=True),
        sa.Column('deadline_description', sa.Text(), nullable=True),
        sa.Column('certainty', sa.String(20), nullable=False, default='medium'),
        sa.Column('source_section', sa.String(100), nullable=True),
        sa.Column('source_page', sa.Integer(), nullable=True),
        sa.Column('source_quote', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('review_status', sa.String(50), nullable=False, default='pending'),
        sa.Column('is_stale', sa.String(10), nullable=False),
        sa.Column('user_edited', sa.String(10), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['contract_version_id'], ['contract_versions.id'], ondelete='CASCADE'),
    )

    # Create review_actions table
    op.create_table(
        'review_actions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('action_type', sa.String(20), nullable=False),
        sa.Column('extracted_item_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('obligation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('previous_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['extracted_item_id'], ['extracted_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['obligation_id'], ['obligations.id'], ondelete='CASCADE'),
    )

    # Create ambiguities table
    op.create_table(
        'ambiguities',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('contract_version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('conflicting_clauses', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('certainty', sa.String(20), nullable=False, default='low'),
        sa.Column('source_sections', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('source_pages', postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column('source_quotes', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('resolved', sa.String(10), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['contract_version_id'], ['contract_versions.id'], ondelete='CASCADE'),
    )

    # Create clarification_questions table
    op.create_table(
        'clarification_questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('contract_version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('related_clauses', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('context', sa.Text(), nullable=True),
        sa.Column('source_sections', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('source_pages', postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column('source_quotes', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('answered', sa.String(10), nullable=False),
        sa.Column('answer', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['contract_version_id'], ['contract_versions.id'], ondelete='CASCADE'),
    )

    # Create ai_runs table
    op.create_table(
        'ai_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('contract_version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', sa.String(100), nullable=False, unique=True),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='started'),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('validation_result', sa.String(50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('response_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['contract_version_id'], ['contract_versions.id'], ondelete='CASCADE'),
    )

    # Create application_logs table
    op.create_table(
        'application_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('log_level', sa.String(20), nullable=False, default='info'),
        sa.Column('contract_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('contract_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('log_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # Create indexes for better query performance
    op.create_index('ix_contracts_status', 'contracts', ['status'])
    op.create_index('ix_contract_versions_contract_id', 'contract_versions', ['contract_id'])
    op.create_index('ix_extracted_items_contract_version_id', 'extracted_items', ['contract_version_id'])
    op.create_index('ix_extracted_items_review_status', 'extracted_items', ['review_status'])
    op.create_index('ix_obligations_contract_version_id', 'obligations', ['contract_version_id'])
    op.create_index('ix_obligations_review_status', 'obligations', ['review_status'])
    op.create_index('ix_obligations_deadline', 'obligations', ['deadline'])
    op.create_index('ix_ai_runs_contract_version_id', 'ai_runs', ['contract_version_id'])
    op.create_index('ix_application_logs_contract_id', 'application_logs', ['contract_id'])
    op.create_index('ix_application_logs_contract_version_id', 'application_logs', ['contract_version_id'])
    op.create_index('ix_application_logs_event_type', 'application_logs', ['event_type'])
    op.create_index('ix_application_logs_created_at', 'application_logs', ['created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_application_logs_created_at', 'application_logs')
    op.drop_index('ix_application_logs_event_type', 'application_logs')
    op.drop_index('ix_application_logs_contract_version_id', 'application_logs')
    op.drop_index('ix_application_logs_contract_id', 'application_logs')
    op.drop_index('ix_ai_runs_contract_version_id', 'ai_runs')
    op.drop_index('ix_obligations_deadline', 'obligations')
    op.drop_index('ix_obligations_review_status', 'obligations')
    op.drop_index('ix_obligations_contract_version_id', 'obligations')
    op.drop_index('ix_extracted_items_review_status', 'extracted_items')
    op.drop_index('ix_extracted_items_contract_version_id', 'extracted_items')
    op.drop_index('ix_contract_versions_contract_id', 'contract_versions')
    op.drop_index('ix_contracts_status', 'contracts')

    # Drop tables
    op.drop_table('application_logs')
    op.drop_table('ai_runs')
    op.drop_table('clarification_questions')
    op.drop_table('ambiguities')
    op.drop_table('review_actions')
    op.drop_table('obligations')
    op.drop_table('extracted_items')
    op.drop_table('parties')
    op.drop_table('contract_versions')
    op.drop_table('contracts')
