#ifndef _LIST_H_
#define _LIST_H_

//LIST FUNCTIONS

ListNode*
liNew(Edge *data);

void
liInsertAfter( ListNode *this, ListNode *add) ;

void
liRemoveAfter( ListNode *this ) ;

void
liRemoveRef( ListNode *dummyhead, Edge* data );

Edge*
liGetData( ListNode *this );

ListNode*
liGetNext( ListNode *this );

#endif