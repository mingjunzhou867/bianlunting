"""Generate seed dictionary artifacts for the cognition preparation layer."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import BaseModel, Field


class DictionarySourceRef(BaseModel):
    table: str
    field: str
    role: str


class DictionaryCandidate(BaseModel):
    name: str
    description: str
    values: dict[str, str]
    common_values: list[str] = Field(default_factory=list)
    source_refs: list[DictionarySourceRef] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class DictionaryArtifact(DictionaryCandidate):
    total_count: int


def build_default_candidates() -> list[DictionaryCandidate]:
    return [
        DictionaryCandidate(
            name="ADC310",
            description="就业困难人员类别",
            values={
                "070": "城镇零就业家庭成员",
                "060": "残疾人",
                "050": "大龄就业困难人员",
                "041": "享受城镇居民最低生活保障的人员",
                "040": "连续失业1年以上的人员",
                "030": "集体企业下岗职工",
                "020": "国企关闭破产安置人员",
                "010": "国企下岗失业人员",
                "993": "离校2年内未就业的高校毕业生",
                "992": "毕业年度高校毕业生",
                "991": "离校1年内未就业的高校毕业生",
                "990": "其他",
                "120": "贫困劳动力",
                "110": "各级社会福利机构供养的成年孤儿和社会成年孤儿",
                "100": "毕业一年以上未就业的高校毕业生",
                "091": "建档立卡贫困人员",
                "080": "生活困难的失地农民（失地农民）",
                "090": "农村零转移就业贫困家庭成员",
            },
            common_values=["050", "993", "990"],
            source_refs=[
                DictionarySourceRef(
                    table="hardship_certification",
                    field="hardship_category",
                    role="primary_code_field",
                ),
            ],
            aliases=["困难人员类别", "就业困难类别"],
            notes=["任务运行时默认只加载相关摘录，不把整本字典全部注入 prompt。"],
        ),
        DictionaryCandidate(
            name="INSURER_STATUS",
            description="社保缴费身份状态",
            values={
                "101": "单位缴纳",
                "102": "灵活就业人员缴纳",
            },
            common_values=["101", "102"],
            source_refs=[
                DictionarySourceRef(
                    table="social_insurance_payment",
                    field="insurer_status",
                    role="payment_status_code",
                ),
            ],
            aliases=["缴费身份状态"],
            notes=["用于区分单位缴费与灵活就业缴费。"],
        ),
        DictionaryCandidate(
            name="EMPLOYMENT_FORM",
            description="就业形式",
            values={
                "灵活就业": "灵活就业",
                "单位就业": "单位就业",
                "创业": "创业",
            },
            common_values=["灵活就业", "单位就业"],
            source_refs=[
                DictionarySourceRef(
                    table="employment_registration",
                    field="employment_form",
                    role="registration_mode",
                ),
            ],
            aliases=["就业方式"],
        ),
        DictionaryCandidate(
            name="COMPANY_TYPE",
            description="工商主体类型",
            values={
                "企业": "企业",
                "个体工商户": "个体工商户",
                "事业单位": "事业单位",
            },
            common_values=["企业", "个体工商户"],
            source_refs=[
                DictionarySourceRef(
                    table="company_info",
                    field="company_type",
                    role="entity_type",
                ),
            ],
            aliases=["主体类型"],
        ),
        DictionaryCandidate(
            name="BUSINESS_ROLE",
            description="人员工商角色",
            values={
                "普通居民": "普通居民",
                "个体工商户": "个体工商户",
                "企业法人": "企业法人",
            },
            common_values=["普通居民", "个体工商户", "企业法人"],
            source_refs=[
                DictionarySourceRef(
                    table="person",
                    field="business_role",
                    role="person_business_identity",
                ),
            ],
            aliases=["工商身份"],
        ),
    ]


def normalize_candidate(candidate: DictionaryCandidate) -> DictionaryArtifact:
    return DictionaryArtifact(
        name=candidate.name,
        description=candidate.description,
        total_count=len(candidate.values),
        common_values=list(candidate.common_values),
        source_refs=list(candidate.source_refs),
        aliases=list(candidate.aliases),
        notes=list(candidate.notes),
        values=dict(candidate.values),
    )


def generate_artifacts(dict_ids: list[str] | None = None) -> list[DictionaryArtifact]:
    selected_ids = {value.upper() for value in dict_ids or []}
    artifacts = []
    for candidate in build_default_candidates():
        if selected_ids and candidate.name.upper() not in selected_ids:
            continue
        artifacts.append(normalize_candidate(candidate))
    return artifacts


def build_manifest(dict_ids: list[str] | None = None) -> list[dict[str, object]]:
    selected = generate_artifacts(dict_ids=dict_ids)
    return [
        {
            "name": artifact.name,
            "description": artifact.description,
            "total_count": artifact.total_count,
            "source_fields": [
                f"{ref.table}.{ref.field}" for ref in artifact.source_refs
            ],
            "output_file": f"{artifact.name}.json",
        }
        for artifact in selected
    ]


def write_artifacts(output_dir: Path, dict_ids: list[str] | None = None) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for artifact in generate_artifacts(dict_ids=dict_ids):
        target = output_dir / f"{artifact.name}.json"
        target.write_text(
            json.dumps(
                artifact.model_dump(mode="json"),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        written.append(target)
    return written


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate seed dictionary artifacts for cognition prep.",
    )
    parser.add_argument(
        "--manifest",
        action="store_true",
        help="Print manifest JSON without writing files.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write generated artifacts into the target directory.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parent.parent / "dicts"),
        help="Output directory for generated dictionary artifacts.",
    )
    parser.add_argument(
        "--dict-id",
        action="append",
        dest="dict_ids",
        default=[],
        help="Generate only selected dictionary IDs. Can be provided multiple times.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = Path(args.output_dir)

    if args.write:
        written = write_artifacts(output_dir=output_dir, dict_ids=args.dict_ids)
        payload = {
            "mode": "write",
            "written": [path.name for path in written],
            "output_dir": str(output_dir),
        }
    else:
        payload = {
            "mode": "manifest" if args.manifest else "dry-run",
            "artifacts": build_manifest(dict_ids=args.dict_ids),
        }

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
