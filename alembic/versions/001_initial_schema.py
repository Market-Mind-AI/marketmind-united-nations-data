"""Initial schema - REST API only

Revision ID: 001
Revises:
Create Date: 2026-06-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ingestion_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(), nullable=False, server_default="united_nations_data"),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column("request_payload", postgresql.JSONB(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ingestion_runs_source", "ingestion_runs", ["source"])
    op.create_index("ix_ingestion_runs_status", "ingestion_runs", ["status"])
    op.create_index("ix_ingestion_runs_started_at", "ingestion_runs", ["started_at"])

    op.create_table(
        "undata_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ingestion_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ingestion_runs.id"), nullable=False),
        sa.Column("endpoint", sa.String(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("dataset_id", sa.String(), nullable=True),
        sa.Column("dataflow_id", sa.String(), nullable=True),
        sa.Column("country", sa.String(), nullable=True),
        sa.Column("indicator_code", sa.String(), nullable=True),
        sa.Column("start_period", sa.String(), nullable=True),
        sa.Column("end_period", sa.String(), nullable=True),
        sa.Column("request_method", sa.String(), nullable=False),
        sa.Column("query_params", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_undata_requests_ingestion_run_id", "undata_requests", ["ingestion_run_id"])
    op.create_index("ix_undata_requests_endpoint", "undata_requests", ["endpoint"])
    op.create_index("ix_undata_requests_dataset_id", "undata_requests", ["dataset_id"])
    op.create_index("ix_undata_requests_dataflow_id", "undata_requests", ["dataflow_id"])
    op.create_index("ix_undata_requests_country", "undata_requests", ["country"])
    op.create_index("ix_undata_requests_indicator_code", "undata_requests", ["indicator_code"])

    op.create_table(
        "raw_api_responses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("undata_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("undata_requests.id"), nullable=False),
        sa.Column("endpoint", sa.String(), nullable=False),
        sa.Column("request_payload", postgresql.JSONB(), nullable=False),
        sa.Column("response_payload", postgresql.JSONB(), nullable=True),
        sa.Column("response_xml", sa.Text(), nullable=True),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_raw_api_responses_undata_request_id", "raw_api_responses", ["undata_request_id"])
    op.create_index("ix_raw_api_responses_endpoint", "raw_api_responses", ["endpoint"])

    op.create_table(
        "undata_dataflows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("undata_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("undata_requests.id"), nullable=True),
        sa.Column("agency_id", sa.String(), nullable=True),
        sa.Column("dataflow_id", sa.String(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.String(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_undata_dataflows_dataflow_id", "undata_dataflows", ["dataflow_id"])
    op.create_index("ix_undata_dataflows_agency_id", "undata_dataflows", ["agency_id"])

    op.create_table(
        "undata_datastructures",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("undata_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("undata_requests.id"), nullable=True),
        sa.Column("dataflow_id", sa.String(), nullable=True),
        sa.Column("structure_id", sa.String(), nullable=True),
        sa.Column("dimension_id", sa.String(), nullable=True),
        sa.Column("dimension_name", sa.Text(), nullable=True),
        sa.Column("dimension_position", sa.Integer(), nullable=True),
        sa.Column("code_id", sa.String(), nullable=True),
        sa.Column("code_name", sa.Text(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_undata_datastructures_dataflow_id", "undata_datastructures", ["dataflow_id"])
    op.create_index("ix_undata_datastructures_structure_id", "undata_datastructures", ["structure_id"])
    op.create_index("ix_undata_datastructures_dimension_id", "undata_datastructures", ["dimension_id"])
    op.create_index("ix_undata_datastructures_code_id", "undata_datastructures", ["code_id"])

    op.create_table(
        "undata_observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("undata_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("undata_requests.id"), nullable=False),
        sa.Column("dataset_id", sa.String(), nullable=True),
        sa.Column("dataflow_id", sa.String(), nullable=True),
        sa.Column("country", sa.String(), nullable=False),
        sa.Column("country_name", sa.Text(), nullable=True),
        sa.Column("indicator_code", sa.String(), nullable=False),
        sa.Column("indicator_name", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(), nullable=True),
        sa.Column("frequency", sa.String(), nullable=True),
        sa.Column("time_period", sa.String(), nullable=False),
        sa.Column("value", sa.Numeric(), nullable=True),
        sa.Column("normalized_value", sa.Numeric(), nullable=True),
        sa.Column("attributes", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_undata_observations_undata_request_id", "undata_observations", ["undata_request_id"])
    op.create_index("ix_undata_observations_dataset_id", "undata_observations", ["dataset_id"])
    op.create_index("ix_undata_observations_dataflow_id", "undata_observations", ["dataflow_id"])
    op.create_index("ix_undata_observations_country", "undata_observations", ["country"])
    op.create_index("ix_undata_observations_indicator_code", "undata_observations", ["indicator_code"])
    op.create_index("ix_undata_observations_time_period", "undata_observations", ["time_period"])

    op.create_table(
        "undata_indicators_catalog",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("indicator_code", sa.String(), nullable=False),
        sa.Column("indicator_name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("expected_unit", sa.String(), nullable=True),
        sa.Column("marketmind_dimension", sa.String(), nullable=True),
        sa.Column("un_indicator_id", sa.Integer(), nullable=True),
        sa.Column("un_location_id", sa.Integer(), nullable=True),
        sa.Column("default_variant_id", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("default_age_id", sa.Integer(), nullable=False, server_default="188"),
        sa.Column("default_sex_id", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("default_category_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_undata_indicators_catalog_indicator_code", "undata_indicators_catalog", ["indicator_code"])
    op.create_index("ix_undata_indicators_catalog_category", "undata_indicators_catalog", ["category"])
    op.create_index("ix_undata_indicators_catalog_marketmind_dimension", "undata_indicators_catalog", ["marketmind_dimension"])
    op.create_index("ix_undata_indicators_catalog_is_active", "undata_indicators_catalog", ["is_active"])
    op.create_index("ix_undata_indicators_catalog_un_indicator_id", "undata_indicators_catalog", ["un_indicator_id"])


def downgrade() -> None:
    op.drop_table("undata_indicators_catalog")
    op.drop_table("undata_observations")
    op.drop_table("undata_datastructures")
    op.drop_table("undata_dataflows")
    op.drop_table("raw_api_responses")
    op.drop_table("undata_requests")
    op.drop_table("ingestion_runs")
