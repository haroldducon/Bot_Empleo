import unittest
from types import SimpleNamespace

from app.matching import _experience_match, _parse_salary_amounts, _required_education_levels, explain_job


def profile(
    *,
    desired_titles=None,
    skills=None,
    experiences=None,
    degrees=None,
    salary_min=None,
    city="Bogotá",
    modality="cualquiera",
):
    return SimpleNamespace(
        desired_titles=desired_titles or [],
        skills=skills or [],
        experiences=experiences or [],
        education=[SimpleNamespace(degree=degree) for degree in (degrees or [])],
        salary_min=salary_min,
        city=city,
        modality=modality,
    )


class MatchingTests(unittest.TestCase):
    def test_salary_missing_is_unknown_not_a_mismatch(self):
        person = profile(
            desired_titles=["Analista de datos"],
            skills=["SQL"],
            experiences=[SimpleNamespace(position="Analista de datos", description="analisis de datos SQL")],
            degrees=["Profesional en Administración de Empresas"],
            salary_min=3_000_000,
        )
        result = explain_job(
            person,
            "Analista de datos",
            "Requiere profesional con conocimientos SQL en Bogotá",
            "Bogotá",
        )
        salary = next(item for item in result["criteria"] if item["key"] == "salario")
        self.assertEqual(result["salary_status"], "unknown")
        self.assertEqual(salary["status"], "unknown")
        self.assertIn("Salario no informado", salary["detail"])
        self.assertNotEqual(result["classification"], "excluded")

    def test_ambiguous_degree_title_goes_to_review(self):
        person = profile(
            desired_titles=["Analista contable"],
            skills=["Excel"],
            degrees=["Administración de Empresas"],
            city="Bogotá",
        )
        result = explain_job(
            person,
            "Analista contable",
            "Se requiere profesional en el área contable. Manejo de Excel en Bogotá.",
            "Bogotá",
        )
        studies = next(item for item in result["criteria"] if item["key"] == "estudios")
        self.assertEqual(studies["status"], "unknown")
        self.assertEqual(result["classification"], "review")
        self.assertTrue(any("nivel educativo" in reason.lower() for reason in result["review_reasons"]))

    def test_related_experience_can_enter_review_below_30_if_salary_is_unknown(self):
        person = profile(
            desired_titles=["Ingeniero aeroespacial"],
            skills=["SAP"],
            experiences=[SimpleNamespace(position="Coordinador de facturación", description="facturación cartera cobros")],
            degrees=["Tecnólogo en Administración"],
            salary_min=2_000_000,
            city="Bogotá",
            modality="presencial",
        )
        result = explain_job(person, "Asesor comercial", "facturación cartera cobros", "Cali")
        self.assertLess(result["score"], 30)
        self.assertEqual(result["salary_status"], "unknown")
        self.assertEqual(result["classification"], "review")
        self.assertTrue(any("experiencia parece claramente relacionada" in reason for reason in result["review_reasons"]))

    def test_low_score_without_related_experience_is_excluded(self):
        person = profile(
            desired_titles=["Ingeniero aeroespacial"],
            skills=["SAP"],
            experiences=[SimpleNamespace(position="Enfermero", description="atención clínica y pacientes")],
            degrees=["Tecnólogo en Enfermería"],
            city="Bogotá",
        )
        result = explain_job(person, "Asesor comercial", "ventas y clientes", "Bogotá")
        self.assertLess(result["score"], 30)
        self.assertEqual(result["classification"], "excluded")

    def test_related_experience_without_profile_salary_target_does_not_trigger_exception(self):
        person = profile(
            desired_titles=["Ingeniero aeroespacial"],
            skills=["SAP"],
            experiences=[SimpleNamespace(position="Coordinador de facturación", description="facturación cartera cobros")],
            degrees=["Tecnólogo en Administración"],
            city="Bogotá",
            modality="presencial",
        )
        result = explain_job(person, "Asesor comercial", "facturación cartera cobros", "Cali")
        self.assertLess(result["score"], 30)
        self.assertEqual(result["salary_status"], "target_missing")
        self.assertEqual(result["classification"], "excluded")

    def test_salary_below_expectation_is_visible_only_for_review(self):
        person = profile(
            desired_titles=["Analista de datos"],
            skills=["SQL"],
            salary_min=3_000_000,
            city="Bogotá",
        )
        result = explain_job(
            person,
            "Analista de datos",
            "Salario: $ 2.000.000 COP. Requiere SQL en Bogotá.",
            "Bogotá",
        )
        self.assertEqual(result["salary_status"], "missing")
        self.assertEqual(result["classification"], "review")
        self.assertTrue(any("salario publicado" in reason.lower() for reason in result["review_reasons"]))

    def test_salary_range_parser_reads_cop_thousands(self):
        self.assertEqual(
            _parse_salary_amounts("Salario: $ 1.500.000 - $ 2.200.000 COP"),
            [1_500_000, 2_200_000],
        )

    def test_one_generic_job_title_is_not_enough_for_strong_experience_exception(self):
        person = profile(
            experiences=[SimpleNamespace(position="Coordinador", description="responsable general de labores")]
        )
        _, status, _, strongly_related = _experience_match(
            person,
            "Coordinador de proyectos",
            "Buscamos coordinador con funciones generales",
        )
        self.assertEqual(status, "partial")
        self.assertFalse(strongly_related)

    def test_education_level_mentioned_without_requirement_context_is_ignored(self):
        levels = _required_education_levels(
            "Buscamos profesional para ventas. Se valora especialización futura, no obligatoria. "
            "Requisito: manejo de Excel, atención al cliente y coordinación durante varios años "
            "con profesionales de distintas áreas."
        )
        self.assertEqual(levels, [])


if __name__ == "__main__":
    unittest.main()
