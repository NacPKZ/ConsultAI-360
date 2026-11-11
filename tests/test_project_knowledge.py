import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from project_knowledge import correct, project_answer, profile

class ProjectKnowledgeTests(unittest.TestCase):
    def test_typo_github(self):
        corrected, fixes = correct('donne mon gitub')
        self.assertIn('github',corrected)
        self.assertTrue(fixes)
        self.assertEqual(project_answer(corrected)['topic'],'Profil')
    def test_navigation(self):
        self.assertIn('Observatoire',project_answer('ou sont les graphiques')['text'])
        self.assertIn('Porte de décision',project_answer('ou se trouve decision gate')['text'])
    def test_project(self):
        self.assertEqual(project_answer('comment fonctionne le projet')['topic'],'Architecture')
        self.assertEqual(project_answer('qui es tu')['topic'],'Identité')
    def test_tools(self):
        self.assertIn('PostgreSQL',project_answer(correct('a quoi sert postgress')[0])['text'])
    def test_no_fake_linkedin(self):
        with patch.dict(os.environ, {'CONSULTAI_LINKEDIN_URL':'https://example.com/fake'}, clear=False):
            self.assertEqual(profile()['linkedin'],'')
    def test_real_linkedin(self):
        with patch.dict(os.environ, {'CONSULTAI_LINKEDIN_URL':'https://www.linkedin.com/in/example-123'}, clear=False):
            self.assertIn('linkedin.com',profile()['linkedin'])
    def test_no_accidental_numeric_change(self):
        self.assertEqual(correct('et si 15 % manquaient')[0],'et si 15 % manquaient')
    def test_no_kpi_hijack(self):
        self.assertIsNone(project_answer('quel est le taux de retard ?'))

if __name__ == '__main__': unittest.main()
