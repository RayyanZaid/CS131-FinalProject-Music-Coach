import React, { useEffect, useState } from "react";
import { db, doc, getDoc } from "./firebaseConfig";
import "./TestCards.css"; // Ensure CSS file is correctly imported
function TestCards({ onCardClick }) {
  const [testCards, setTestCards] = useState([]);

  useEffect(() => {
    const fetchTestCards = async () => {
      const docRef = doc(db, "users", "user1");
      const docSnap = await getDoc(docRef);

      if (docSnap.exists()) {
        const data = docSnap.data();
        if (data.tests) {
          const tests = data.tests.map((test) => ({
            name: test.name,
            postureGrade: Math.round(test.postureGrade),
            postureFeedbackArray: test.postureFeedbackArray,
            musicGrade: test.musicGrade,
            musicFeedbackArray: test.musicFeedbackArray,
          }));
          setTestCards(tests.reverse());
        } else {
          console.log("Tests data not available.");
          setTestCards([]);
        }
      } else {
        console.log("No such document!");
        setTestCards([]);
      }
    };

    fetchTestCards();
  }, []);

  return (
    <div className="test-cards-container">
      <h1 className="title-text">Test Cards</h1>
      <div className="cards-scroll-container">
        {testCards.length > 0 ? (
          testCards.map((card, index) => (
            <div className="card" key={index} onClick={() => onCardClick(card)}>
              <h2>{card.name}</h2>
              <p>Posture: {card.postureGrade}%</p>
              {card.musicGrade && <p>Music: {card.musicGrade}%</p>}
            </div>
          ))
        ) : (
          <p>No test data available.</p>
        )}
      </div>
    </div>
  );
}

export default TestCards;
